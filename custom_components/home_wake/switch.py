import logging
import asyncio
import aiohttp
from wakeonlan import send_magic_packet
import asyncssh
import platform
import subprocess
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import (
    DOMAIN,
    CONF_DEVICE_TYPE, 
    DEVICE_TYPE_WINDOWS, DEVICE_TYPE_LINUX, DEVICE_TYPE_VM
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    config = entry.data
    _LOGGER.info(f"config: {config}")
    async_add_entities([WakeOnLanSwitch(config)])

class WakeOnLanSwitch(SwitchEntity):
    def __init__(self, config):
        self._config = config
        self._state = False
        asyncio.create_task(self._check_initial_state())

    async def _check_initial_state(self):
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', self._config["ip"]]
            response = await self.hass.async_add_executor_job(
                subprocess.call, 
                command,
                subprocess.DEVNULL
            )
            self._state = response == 0
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Error checking initial device status: {e}")
            self._state = False

    @property
    def name(self):
        return self._config.get("name")

    @property
    def is_on(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._config.get('name')}_{self._config.get('device_type')}_switch"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._config.get("name"),
            "manufacturer": "XG",
            "model": self._config.get("device_type")
        }

    async def async_update(self):
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', self._config["ip"]]
            response = await self.hass.async_add_executor_job(
                subprocess.call, 
                command,
                subprocess.DEVNULL
            )
            self._state = response == 0
        except Exception as e:
            _LOGGER.error(f"Error checking device status: {e}")
            self._state = False

    async def async_turn_on(self):
        try:
            device_type = self._config[CONF_DEVICE_TYPE]
            if device_type == DEVICE_TYPE_VM:
                # SSH连接配置
                ssh_options = {
                    'host': self._config["ip"],
                    'username': 'root',
                    'client_keys': [self._config["ssh_key"]],
                    'port': self._config["port"],
                    'known_hosts': None,
                }
                
                async with asyncssh.connect(**ssh_options) as conn:
                    await conn.run(self._config["poweron_command"])
            else:
                send_magic_packet(self._config["mac"])
            self._state = True
        except Exception as e:
            _LOGGER.error(f"Failed to turn on device: {e}")

    async def async_turn_off(self):
        try:
            device_type = self._config[CONF_DEVICE_TYPE]
            if device_type == DEVICE_TYPE_WINDOWS:
                # Windows关机
                url = f"http://{self._config['ip']}:{self._config['port']}/?action=System.Shutdown"
                async with aiohttp.ClientSession() as session:
                    await session.get(url)
            
            elif device_type in [DEVICE_TYPE_LINUX, DEVICE_TYPE_VM]:
                # SSH连接配置
                ssh_options = {
                    'host': self._config["ip"],
                    'username': 'root',
                    'client_keys': [self._config["ssh_key"]],
                    'port': self._config["port"],
                    'known_hosts': None,
                }
                
                async with asyncssh.connect(**ssh_options) as conn:
                    if device_type == DEVICE_TYPE_LINUX:
                        await conn.run('poweroff')
                    else:
                        await conn.run(self._config["shutdown_command"])
            
            self._state = False
        except Exception as e:
            _LOGGER.error(f"Failed to turn off device: {e}")
