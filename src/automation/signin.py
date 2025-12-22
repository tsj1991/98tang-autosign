"""
签到核心模块

提供网站登录和签到的核心功能
"""

import re
import logging
from typing import Optional, Dict, Any

from ..browser.helpers import BrowserHelper
from ..browser.element_finder import ElementFinder
from ..utils.timing import TimingManager


class SignInManager:
    """签到管理器"""

    def __init__(
        self, driver, config: Dict[str, Any], logger: Optional[logging.Logger] = None
    ):
        self.driver = driver
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.element_finder = ElementFinder(driver, self.logger)

        # 网站配置
        self.base_url = config.get("base_url", "https://www.sehuatang.org")
        self.home_url = self.base_url

        # 账号配置
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.enable_security_question = config.get("enable_security_question", False)
        self.security_question = config.get("security_question", "")
        self.security_answer = config.get("security_answer", "")

    # =========================
    # 年龄验证
    # =========================
    def handle_age_verification(self) -> bool:
        try:
            age_selectors = [
                "a[href*='agecheck']",
                "//a[contains(text(), '满18岁')]",
                "//a[contains(text(), '请点此进入')]",
            ]
            link = self.element_finder.find_by_selectors(age_selectors, timeout=3)
            if link:
                self.logger.info("检测到年龄验证，正在点击")
                BrowserHelper.safe_click(self.driver, link, self.logger)
                TimingManager.smart_page_wait(
                    self.driver, ["body", "#main", ".wp"], self.logger
                )
            return True
        except Exception as e:
            self.logger.warning(f"年龄验证处理失败: {e}")
            return True

    # =========================
    # 登录表单填写
    # =========================
    def fill_login_form(self) -> bool:
        try:
            username_input = self.element_finder.find_by_selectors(
                ["input[name='username']", "#username"]
            )
            if not username_input:
                self.logger.error("未找到用户名输入框")
                return False

            password_input = self.element_finder.find_by_selectors(
                ["input[name='password']", "#password"]
            )
            if not password_input:
                self.logger.error("未找到密码输入框")
                return False

            username_input.clear()
            username_input.send_keys(self.username)

            password_input.clear()
            password_input.send_keys(self.password)

            return True
        except Exception as e:
            self.logger.error(f"填写登录表单失败: {e}")
            return False

    # =========================
    # 安全提问
    # =========================
    def handle_security_question(self) -> bool:
        if not self.enable_security_question:
            return True

        try:
            question_select = self.element_finder.find_by_selectors(
                ["select[name='questionid']", "#questionid"]
            )
            if not question_select:
                return True

            from selenium.webdriver.common.by import By

            options = question_select.find_elements(By.TAG_NAME, "option")
            for opt in options:
                if self.security_question in opt.text:
                    opt.click()
                    break

            answer_input = self.element_finder.find_by_selectors(
                ["input[name='answer']", "#answer"]
            )
            if answer_input:
                answer_input.clear()
                answer_input.send_keys(self.security_answer)

            return True
        except Exception as e:
            self.logger.error(f"安全提问处理失败: {e}")
            return False

    # =========================
    # 登录状态检查
    # =========================
    def check_login_status(self) -> bool:
        try:
            indicators = [
                "//a[contains(text(),'退出')]",
                "//a[contains(@href,'logout')]",
                ".vwmy",
            ]
            el = self.element_finder.find_by_selectors(indicators, timeout=3)
            return bool(el)
        except Exception:
            return False

    def check_login_error_message(self) -> Optional[str]:
        page = self.driver.page_source
        errors = [
            "用户名或密码错误",
            "密码错误次数过多",
            "账号已被禁用",
            "登录失败",
        ]
        for e in errors:
            if e in page:
                return e
        return None

    # =========================
    # ✅ 唯一登录入口（重点）
    # =========================
    def login(self) -> bool:
        """
        登录网站（直达登录页）
        """
        try:
            self.logger.info("开始登录流程（直达登录页）")

            login_url = f"{self.base_url}/member.php?mod=logging&action=login"
            self.driver.get(login_url)
            TimingManager.smart_wait(
                TimingManager.PAGE_LOAD_DELAY, 1.0, self.logger
            )

            self.handle_age_verification()

            if not self.fill_login_form():
                return False

            self.handle_security_question()

            submit_button = self.element_finder.find_clickable_by_selectors(
                ["#loginsubmit", "button[type='submit']", "input[type='submit']"],
                timeout=5,
            )
            if not submit_button:
                self.logger.error("未找到登录提交按钮")
                return False

            BrowserHelper.safe_click(self.driver, submit_button, self.logger)
            TimingManager.smart_wait(
                TimingManager.PAGE_LOAD_DELAY, 1.5, self.logger
            )

            if self.check_login_status():
                self.logger.info("✅ 登录成功")
                return True

            error = self.check_login_error_message()
            if error:
                self.logger.error(f"登录失败: {error}")

            return False

        except Exception as e:
            self.logger.error(f"登录异常: {e}")
            return False
