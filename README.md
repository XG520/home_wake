# Home Wake 组件

这是一个用于Home Assistant的自定义组件，可以实现远程开关机功能，支持Windows、Linux以及其他设备类型。

## 功能特点

- 支持Wake-on-LAN远程开机
- 支持Windows系统远程关机
- 支持Linux系统SSH远程关机
- 支持自定义设备（如虚拟机）的开关机命令
- 实时监控设备在线状态

## 安装说明
### 方式一：HACS一键安装（推荐）
1. 确保已经安装了 [HACS](https://hacs.xyz/)
2. 在HACS中点击"自定义存储库"
3. 添加此仓库地址：`https://github.com/XG520/home_wake`
4. 类别选择"集成"
5. 点击"添加"
6. 在HACS的集成页面中搜索"离线唤醒"
7. 点击"下载"进行安装
8. 重启Home Assistant

### 方式二：手动安装
1. 将`custom_components/home_wake`文件夹复制到你的Home Assistant配置目录下的`custom_components`文件夹中
2. 重启Home Assistant
3. 在集成页面中搜索"离线唤醒"并添加

## 配置说明

### Windows设备
- 设备名称
- IP地址
- MAC地址
- 端口号（默认8000）

### Linux设备
- 设备名称
- IP地址
- MAC地址
- SSH密钥文件
- SSH端口（默认22）

### 其他设备（如虚拟机）
- 设备名称
- IP地址
- SSH密钥文件（可选）
- SSH端口（默认22）
- 开机命令
- 关机命令

## 依赖项

- wakeonlan >= 2.0.0
- asyncssh >= 2.12.0
- aiohttp >= 3.8.0
- aiofiles >= 23.2.1

## 注意事项

1. Windows设备需要安装Airytec Switch Off 实现关机
2. Linux设备需要配置免密SSH登录
3. 确保目标设备已正确配置Wake-on-LAN功能
4. SSH密钥文件权限会自动设置为600

## 支持

如有问题，请在Github上提交Issue，或加企鹅群：964512589。

## 作者

@XG520