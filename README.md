# AutoTaskPlugin

---

加群push群主更新，反馈bug,交流

[![QQ群](https://img.shields.io/badge/QQ群-965312424-green)](https://qm.qq.com/cgi-bin/qm/qr?k=en97YqjfYaLpebd9Nn8gbSvxVrGdIXy2&jump_from=webapi&authKey=41BmkEjbGeJ81jJNdv7Bf5EDlmW8EHZeH7/nktkXYdLGpZ3ISOS7Ur4MKWXC7xIx)

## 安装

配置完成 [LangBot](https://github.com/RockChinQ/LangBot) 主程序后使用管理员账号向机器人发送命令即可安装：

```
!plugin get <你的插件发布仓库地址>
```

或查看详细的[插件安装说明](https://docs.langbot.app/plugin/plugin-intro.html#%E6%8F%92%E4%BB%B6%E7%94%A8%E6%B3%95)

## 功能特性

### 命令列表

| 命令格式                | 功能描述       | 示例                  |
| :---------------------- | :------------- | :-------------------- |
| `🕒 添加 <任务名> <时间>` | 创建新定时任务 | `🕒 添加 早报 7:00` |
| `🕒 删除 <任务名>`      | 删除现有任务   | `🕒 删除 测试任务`  |
| `🕒 列出`             | 查看所有任务   | `🕒 列出`           |

也可以使用 `@AutoTaskPlugin` 前缀代替 `🕒`：

| 命令格式                | 功能描述       | 示例                  |
| :---------------------- | :------------- | :-------------------- |
| `@AutoTaskPlugin 添加 <任务名> <时间>` | 创建新定时任务 | `@AutoTaskPlugin 添加 早报 7:00` |
| `@AutoTaskPlugin 删除 <任务名>`      | 删除现有任务   | `@AutoTaskPlugin 删除 测试任务`  |
| `@AutoTaskPlugin 列出`             | 查看所有任务   | `@AutoTaskPlugin 列出`           |


**任务名仅能触发/data目录下脚本**

## 使用

自定义功能
脚本需放置在 data/ 目录
<!-- 插件开发者自行填写插件使用说明 -->

## 更新历史

v0.5 修复适配器处理问题，增强帮助信息显示，动态列出可用脚本
v0.4 添加对@AutoTaskPlugin前缀的支持，可以使用@AutoTaskPlugin代替🕒
v0.3 将命令前缀从"/定时"改为"🕒"，避免被ignore-rules过滤
v0.2 初始化定时功能