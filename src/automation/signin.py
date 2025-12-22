"""
签到核心模块

提供网站登录和签到的核心功能
"""

import os
import logging
from typing import Optional, Dict, Any

from ..browser.helpers import BrowserHelper
from ..browser.element_finder import ElementFinder
from ..utils.timing import TimingManager


class SignInManager:
    def __init__(
        self, driver, config: Dict[str, Any], logger: Optional[logging.Logger] = None
    ):
        self.driver = driver
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.element_finder = ElementFinder(driver, self.logger)

        self.base_url = config.get("base_url", "https://www.sehuatang.org")

    # =========================
    # 登录状态判断
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

    # =========================
    # 登录（Cookie 优先）
    # =========================
    def login(self) -> bool:
        try:
            cookies_str = os.getenv("SITE_COOKIES", "").strip()
            if cookies_str:
                self.logger.info("检测到 SITE_COOKIES，尝试使用 Cookie 登录")

                # ⚠️ 必须先访问域名
                self.driver.get(self.base_url)
                TimingManager.smart_wait(
                    TimingManager.PAGE_LOAD_DELAY, 1.5, self.logger
                )

                # ✅ 关键修复：只设置 name + value
                for cookie in cookies_str.split(";"):
                    if "=" not in cookie:
                        continue
                    name, value = cookie.strip().split("=", 1)
                    try:
                        self.driver.add_cookie({
                            "name": name,
                            "value": value,
                        })
                    except Exception as e:
                        self.logger.debug(f"添加 Cookie 失败: {name}, {e}")

                # 刷新页面
                self.driver.get(self.base_url)
                TimingManager.smart_wait(
                    TimingManager.PAGE_LOAD_DELAY, 2.0, self.logger
                )

                if self.check_login_status():
                    self.logger.info("✅ Cookie 登录成功")
                    return True
                else:
                    self.logger.warning("❌ Cookie 登录未生效")

            self.logger.error("未能通过 Cookie 登录，终止登录流程")
            return False

        except Exception as e:
            self.logger.error(f"登录异常: {e}")
            return False
