#!/usr/bin/env python3
"""
微信公众号AI写作助手 - 配置向导

首次使用时引导用户完成配置
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional


def print_header():
    """打印欢迎信息"""
    print("\n" + "=" * 60)
    print("  ✨ AI写作助手 - 初次设置")
    print("=" * 60)
    print("\n让我们花几分钟完成设置，之后就可以开始创作了...\n")


def detect_env_var(var_name: str) -> Optional[str]:
    """检测环境变量"""
    value = os.getenv(var_name)
    if value:
        # 只显示前8个字符
        masked = value[:8] + "..." if len(value) > 8 else value
        return value, masked
    return None, None


def ask_with_default(prompt: str, default: str = None, required: bool = True) -> str:
    """询问用户输入，支持默认值"""
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "

    while True:
        value = input(prompt_text).strip()
        if not value and default:
            return default
        if not value and required:
            print("  ⚠️  此项为必填项，请输入")
            continue
        if not value and not required:
            return None
        return value


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """询问是/否问题"""
    default_text = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{prompt} ({default_text}): ").strip().lower()
        if not answer:
            return default
        if answer in ['y', 'yes', '是']:
            return True
        if answer in ['n', 'no', '否']:
            return False
        print("  ⚠️  请输入 y 或 n")


def setup_llm_config() -> dict:
    """配置LLM服务"""
    print("\n=== 第1步：文章生成服务 ===")
    print("这个服务会帮你写文章内容\n")

    # 检测环境变量
    env_key, masked_key = detect_env_var("DEEPSEEK_API_KEY")

    if env_key:
        print(f"✅ 检测到已保存的密钥: {masked_key}")
        if ask_yes_no("要用这个吗"):
            api_key = env_key
        else:
            api_key = ask_with_default("请输入你的DeepSeek密钥")
    else:
        print("💡 提示：DeepSeek是一个AI服务，需要注册账号获取密钥")
        print("   注册地址：https://platform.deepseek.com\n")
        api_key = ask_with_default("请输入你的DeepSeek密钥")

    base_url = ask_with_default("API地址", "https://api.deepseek.com", required=False)
    model = ask_with_default("模型名称", "deepseek-chat", required=False)

    return {
        "api_key": api_key,
        "base_url": base_url or "https://api.deepseek.com",
        "model": model or "deepseek-chat"
    }


def setup_image_config() -> dict:
    """配置图片生成服务"""
    print("\n=== 第2步：图片生成服务 ===")
    print("这个服务会帮你生成文章配图\n")

    # 检测环境变量
    env_key, masked_key = detect_env_var("ARK_API_KEY")

    if env_key:
        print(f"✅ 检测到已保存的密钥: {masked_key}")
        if ask_yes_no("要用这个吗"):
            api_key = env_key
        else:
            api_key = ask_with_default("请输入你的图片生成服务密钥")
    else:
        print("💡 提示：这是火山引擎的AI绘图服务")
        print("   注册地址：https://console.volcengine.com/ark\n")
        api_key = ask_with_default("请输入你的图片生成服务密钥")

    base_url = ask_with_default(
        "API地址",
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        required=False
    )
    model = ask_with_default("模型名称", "doubao-seedream-4-5-251128", required=False)

    return {
        "api_key": api_key,
        "base_url": base_url or "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        "model": model or "doubao-seedream-4-5-251128"
    }


def setup_wechat_config() -> dict:
    """配置微信公众号"""
    print("\n=== 第3步：微信公众号 ===")
    print("这样才能把文章发布到你的公众号\n")

    # 检测环境变量
    env_appid, masked_appid = detect_env_var("WECHAT_APPID")
    env_secret, masked_secret = detect_env_var("WECHAT_SECRET")

    if env_appid:
        print(f"✅ 检测到已保存的AppID: {masked_appid}")
        if ask_yes_no("要用这个吗"):
            appid = env_appid
        else:
            appid = ask_with_default("请输入你的公众号AppID")
    else:
        print("💡 提示：在微信公众平台 > 设置与开发 > 基本配置 中可以找到")
        print("   地址：https://mp.weixin.qq.com\n")
        appid = ask_with_default("请输入你的公众号AppID")

    if env_secret:
        print(f"✅ 检测到已保存的AppSecret: {masked_secret}")
        if ask_yes_no("要用这个吗"):
            secret = env_secret
        else:
            secret = ask_with_default("请输入你的公众号AppSecret")
    else:
        secret = ask_with_default("请输入你的公众号AppSecret")

    # 检测当前IP
    print("\n正在检测你的服务器IP...")
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"检测到: {local_ip}")
    except:
        local_ip = None

    print("\n⚠️  重要提醒：")
    print("   需要把服务器IP加入微信公众号的白名单")
    print("   位置：微信公众平台 > 设置与开发 > 基本配置 > IP白名单")

    if local_ip:
        server_ip = ask_with_default("服务器IP", local_ip, required=False)
    else:
        server_ip = ask_with_default("服务器IP（可选）", required=False)

    return {
        "appid": appid,
        "secret": secret,
        "server_ip": server_ip
    }


def setup_content_config() -> dict:
    """配置内容相关"""
    print("\n=== 第4步：个性化设置 ===\n")

    author = ask_with_default("文章作者署名", "日新", required=False)

    print("\n文章保存位置：")
    print("  默认会保存在工具目录下的 output/ 文件夹")
    use_custom = ask_yes_no("要自定义保存位置吗", default=False)

    if use_custom:
        output_dir = ask_with_default("保存位置", required=False)
    else:
        output_dir = None

    return {
        "author": author or "日新",
        "output_dir": output_dir
    }


def setup_prompts_config() -> dict:
    """配置提示词"""
    print("\n=== 第5步：写作风格 ===\n")

    print("提示词决定了文章的风格和配图的样式")
    print("选项：")
    print("  1) 使用默认风格（推荐，适合大多数情况）")
    print("  2) 自定义风格（高级选项）")

    choice = ask_with_default("你的选择", "1", required=False)

    use_custom = choice == "2"

    if use_custom:
        print("\n你可以稍后编辑 config/prompts.user.json 来自定义风格")
        print("参考 config/prompts.default.json 的格式")

    return {
        "use_custom_prompts": use_custom
    }


def save_config(credentials: dict, settings: dict):
    """保存配置文件"""
    config_dir = Path(__file__).parent / "config"
    config_dir.mkdir(exist_ok=True)

    # 保存凭证
    credentials_file = config_dir / "credentials.json"
    with open(credentials_file, "w", encoding="utf-8") as f:
        json.dump(credentials, f, indent=2, ensure_ascii=False)

    # 保存设置
    settings_file = config_dir / "settings.json"
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 配置已保存到：")
    print(f"   - {credentials_file}")
    print(f"   - {settings_file}")


def main():
    """主函数"""
    try:
        print_header()

        # 收集配置
        llm_config = setup_llm_config()
        image_config = setup_image_config()
        wechat_config = setup_wechat_config()
        content_config = setup_content_config()
        prompts_config = setup_prompts_config()

        # 组装配置
        credentials = {
            "llm": llm_config,
            "image": image_config,
            "wechat": {
                "appid": wechat_config["appid"],
                "secret": wechat_config["secret"]
            }
        }

        settings = {
            "author": content_config["author"],
            "output_dir": content_config["output_dir"],
            "server_ip": wechat_config.get("server_ip"),
            "use_custom_prompts": prompts_config["use_custom_prompts"]
        }

        # 保存配置
        save_config(credentials, settings)

        print("\n" + "=" * 60)
        print("  ✅ 设置完成！")
        print("=" * 60)
        print("\n现在你可以开始创作了：")
        print("  python skill.py")
        print()

    except KeyboardInterrupt:
        print("\n\n👋 设置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 设置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
