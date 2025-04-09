import os
import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from typing import Any, Dict, Optional
from homeassistant.helpers import selector
import aiofiles
from .const import (
    DOMAIN, CONF_DEVICE_NAME, CONF_TARGET_IP, CONF_SSH_KEY,
    CONF_PORT, CONF_DEVICE_TYPE, CONF_CUSTOM_CMD, CONF_MAC,
    DEVICE_TYPE_WINDOWS, DEVICE_TYPE_LINUX, DEVICE_TYPE_VM,
    SSH_KEY_PATH, CONF_POWER_ON_CMD
)
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class WakeOnLanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_DEVICE_NAME):
                errors["base"] = "name_required"
            else:
                self._data.update(user_input)
                return await self.async_step_network()

        # 第一步:名称和设备类型
        data_schema = vol.Schema({
            vol.Required(CONF_DEVICE_NAME): str,
            vol.Required(CONF_DEVICE_TYPE): vol.In({
                DEVICE_TYPE_WINDOWS: "Windows",
                DEVICE_TYPE_LINUX: "Linux",
                DEVICE_TYPE_VM: "其他设备"
            }),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_network(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        device_type = self._data[CONF_DEVICE_TYPE]

        if user_input is not None:
            if not user_input.get(CONF_TARGET_IP):
                errors["base"] = "ip_required"
            elif device_type != DEVICE_TYPE_VM and not user_input.get(CONF_MAC):
                errors["base"] = "mac_required"
            else:
                self._data.update(user_input)
                return await self.async_step_options()

        # 第二步:网络配置
        schema = {
            vol.Required(CONF_TARGET_IP): str,
        }
        
        # 非VM设备需要MAC地址
        if device_type != DEVICE_TYPE_VM:
            schema[vol.Required(CONF_MAC)] = str

        return self.async_show_form(
            step_id="network",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def _process_ssh_key(self, user_input: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
        """异步处理 SSH 密钥文件"""
        errors = {}
        try:
            # 获取上传目录路径
            upload_dir = Path('/tmp/home-assistant-file_upload') / user_input[CONF_SSH_KEY]
            logger.info(f"Upload directory: {upload_dir}")
            
            # 异步获取目录中的文件
            try:
                # 使用 asyncio.to_thread 在线程池中执行阻塞操作
                uploaded_files = await asyncio.to_thread(lambda: [f.name for f in upload_dir.iterdir()])
            except OSError as e:
                logger.error(f"Error accessing upload directory: {e}")
                errors["base"] = "ssh_key_failed"
                return False, errors
                
            if not uploaded_files:
                errors["base"] = "ssh_key_failed"
                return False, errors
                
            uploaded_file = upload_dir / uploaded_files[0]
            
            # 验证密钥格式
            async with aiofiles.open(uploaded_file, 'r') as f:
                content = await f.read()
                if not all(x in content for x in ['BEGIN', 'PRIVATE KEY', 'END']):
                    errors["base"] = "invalid_ssh_key"
                    return False, errors

            # 准备目标路径
            component_path = Path(__file__).parent
            key_dir = component_path / SSH_KEY_PATH
            await asyncio.to_thread(key_dir.mkdir, exist_ok=True)
            
            key_filename = f"{self._data[CONF_DEVICE_NAME]}.key"
            key_file = key_dir / key_filename
            
            # 复制文件
            async with aiofiles.open(uploaded_file, 'rb') as src, \
                       aiofiles.open(key_file, 'wb') as dst:
                content = await src.read()
                await dst.write(content)
            
            # 设置权限
            await asyncio.to_thread(lambda: key_file.chmod(0o600))
            user_input[CONF_SSH_KEY] = str(key_file)
            return True, errors

        except Exception as e:
            logger.error(f"Error processing SSH key file: {e}")
            errors["base"] = "ssh_key_failed"
            return False, errors

    async def async_step_options(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}
        device_type = self._data[CONF_DEVICE_TYPE]

        if user_input is not None:
            if device_type == DEVICE_TYPE_LINUX and not user_input.get(CONF_SSH_KEY):
                errors["base"] = "ssh_key_required"
            elif device_type == DEVICE_TYPE_VM:
                if not user_input.get(CONF_POWER_ON_CMD):
                    errors["base"] = "poweron_cmd_required"
                elif not user_input.get(CONF_CUSTOM_CMD):
                    errors["base"] = "shutdown_cmd_required"
            
            if not errors:
                if device_type in [DEVICE_TYPE_LINUX, DEVICE_TYPE_VM] and user_input.get(CONF_SSH_KEY):
                    success, file_errors = await self._process_ssh_key(user_input)
                    if not success:
                        errors.update(file_errors)

                if not errors:
                    self._data.update(user_input)
                    return self.async_create_entry(
                        title=self._data[CONF_DEVICE_NAME],
                        data=self._data
                    )

        # 第三步:根据设备类型的特定配置
        schema = {}
        if device_type == DEVICE_TYPE_WINDOWS:
            schema.update({
                vol.Optional(CONF_PORT, default=8000): cv.port,
            })
        elif device_type == DEVICE_TYPE_LINUX:
            schema.update({
                vol.Optional(CONF_PORT, default=22): cv.port,
                vol.Required(CONF_SSH_KEY): selector.FileSelector(
                    selector.FileSelectorConfig(
                        accept=".key,.pem",
                    )
                ),
            })
        elif device_type == DEVICE_TYPE_VM:
            schema.update({
                vol.Optional(CONF_PORT, default=22): cv.port,
                vol.Optional(CONF_SSH_KEY): selector.FileSelector(
                    selector.FileSelectorConfig(
                        accept=".key,.pem",
                    )
                ),
                vol.Required(CONF_POWER_ON_CMD): str,
                vol.Required(CONF_CUSTOM_CMD): str,
            })

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
