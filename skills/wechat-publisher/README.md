# ✨ AI写作助手

一键生成高质量公众号文章，自动配图，支持发布到微信公众号。

**这是一个OpenClaw Skill，通过自然语言对话即可使用。**

## ⚠️ 安全提示

**本项目不包含任何真实的API密钥或凭证信息。**

所有敏感信息都需要你自己配置，配置文件已被 `.gitignore` 忽略，不会被提交到git。

## 快速开始

### 1. 安装

```bash
# 克隆仓库（私有仓库需要访问令牌）
git clone https://你的令牌@gitee.com/woipanda/openclaw-wechat-publisher.git
cd openclaw-wechat-publisher

# 安装依赖
pip install -r requirements.txt
```

**一键安装脚本（推荐）：**
```bash
# 下载并运行安装脚本
curl -O https://gitee.com/woipanda/openclaw-wechat-publisher/raw/master/install.sh
bash install.sh
```

### 2. 初次设置

首次使用时，运行：
```bash
python setup.py
```

设置向导会友好地引导你完成配置：
1. **文章生成服务**（DeepSeek - 用于写文章）
2. **图片生成服务**（火山引擎 - 用于生成配图）
3. **微信公众号**（AppID、AppSecret）
4. **个性化设置**（作者署名、保存位置）
5. **写作风格**（使用默认或自定义）
cp config/settings.example.json config/settings.json

# 编辑配置文件，填入真实信息
nano config/credentials.json
nano config/settings.json
```

**方式3：环境变量**
```bash
# 设置环境变量（可选，配置向导会自动检测）
export DEEPSEEK_API_KEY="sk-your-key"
export ARK_API_KEY="your-key"
export WECHAT_APPID="your-appid"
export WECHAT_SECRET="your-secret"
```

### 3. 使用

**在OpenClaw中使用（推荐）：**

直接和OpenClaw对话，它会自动调用这个Skill：

```
你：帮我写一篇关于AI写作技巧的文章
OpenClaw：✨ 正在创作关于「AI写作技巧」的文章...
```

```
你：参考这篇文章帮我写一篇类似的：[粘贴文章内容]
OpenClaw：✨ 正在参考文章风格创作...
```

**命令行调用（开发/测试）：**

```bash
# 主题模式
python skill.py "AI写作的3个实用技巧"

# 参考文章模式
python skill.py --reference "参考文章内容..."

# 生成并发布
python skill.py "AI写作技巧" --publish
```

## 功能特性

- ✅ **两种创作模式**
  - 主题模式：输入主题，AI创作原创内容
  - 参考文章模式：提供爆款文章，生成类似风格
- ✅ **AI生成文章**（2000-3000字高质量内容）
- ✅ **自动生成标题**（6个候选标题供选择）
- ✅ **智能配图**（3-4张信息可视化风格图片）
- ✅ **发布到微信**（一键发布到公众号草稿箱）
- ✅ **友好交互**（无需编程基础，对话式操作）
- ✅ **灵活配置**（支持自定义风格和提示词）

## 配置文件说明

### 文件结构

```
config/
├── credentials.example.json    # 敏感信息模板（可提交git）
├── credentials.json            # 真实凭证（不提交git）
├── settings.example.json       # 普通配置模板（可提交git）
├── settings.json               # 真实配置（不提交git）
├── prompts.default.json        # 默认提示词（可提交git）
└── prompts.user.json           # 自定义提示词（不提交git）
```

### 必需配置项

1. **LLM服务**（用于生成文章内容）
   - DeepSeek API密钥（推荐）
   - 或其他兼容OpenAI格式的API

2. **图片生成服务**（用于生成配图）
   - Ark/Seedream API密钥

3. **微信公众号凭证**（用于发布文章）
   - AppID
   - AppSecret
   - 服务器IP（用于白名单检测）

4. **内容配置**
   - 作者署名（默认：日新）
   - 输出目录（可选）

### 安全说明

- ❌ **不要**将 `credentials.json` 提交到git
- ❌ **不要**在公开仓库中包含真实API密钥
- ✅ **务必**检查 `.gitignore` 是否正确配置
- ✅ **建议**使用环境变量存储敏感信息

## 自定义提示词

如果你想自定义文章风格、标题风格或图片风格：

```bash
# 复制默认提示词
cp config/prompts.default.json config/prompts.user.json

# 编辑自定义提示词
nano config/prompts.user.json

# 在 settings.json 中启用自定义提示词
{
  "use_custom_prompts": true
}
```

## 云服务器部署

### 部署步骤

1. 将代码上传到服务器
2. 配置微信IP白名单（添加服务器IP）
3. 运行配置向导
4. 测试生成功能

详细步骤请参考项目中的部署文档。

## 常见问题

### 1. 微信IP白名单错误（40164）

**问题**：调用微信API时返回错误码40164

**解决**：
1. 登录微信公众号后台
2. 进入"设置与开发" > "基本配置" > "IP白名单"
3. 添加你的服务器IP地址
4. 等待5-10分钟生效

### 2. DeepSeek API余额不足

**问题**：生成文章时返回402错误

**解决**：
1. 登录 https://platform.deepseek.com
2. 充值账户余额
3. 重新运行命令

### 3. 图片生成失败

**问题**：文章生成成功但没有配图

**解决**：
1. 检查Ark API密钥是否正确
2. 检查API余额是否充足
3. 查看日志文件排查具体错误

### 4. 如何获取私有仓库访问权限

**问题**：git clone时提示无权限

**解决**：
1. 联系仓库所有者获取访问令牌
2. 使用带令牌的URL克隆：`git clone https://令牌@gitee.com/woipanda/openclaw-wechat-publisher.git`

## 开发路线图

- [x] 文章内容生成
- [x] 标题生成
- [x] 智能配图
- [x] 交互式配置
- [ ] 一键发布到微信
- [ ] 批量生成
- [ ] 定时发布

## 许可证

MIT License

## 作者

日新

---

**⚠️ 再次提醒：请妥善保管你的API密钥，不要泄露给他人！**
