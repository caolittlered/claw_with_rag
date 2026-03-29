# 邮箱验证配置指南

## 📧 功能概述

注册流程现在包含以下安全验证：

1. **行为验证（真人验证）** - 简单的数学题目，防止机器人批量注册
2. **邮箱验证码** - 验证邮箱真实性，防止虚假注册
3. **频率限制** - 防刷机制，限制发送次数

---

## ⚙️ 配置步骤

### 1. 配置 SMTP 邮箱

编辑 `config/config.yaml`：

#### Gmail 配置示例
```yaml
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "your-email@gmail.com"
  smtp_password: "your-app-password"  # 不是登录密码！是应用专用密码
  from_name: "Suni AI"
  from_email: "noreply@suniai.com"
  use_tls: true
```

**获取 Gmail 应用专用密码：**
1. 开启两步验证：https://myaccount.google.com/security
2. 生成应用密码：https://myaccount.google.com/apppasswords
3. 选择「邮件」→ 生成16位密码

#### QQ邮箱配置示例
```yaml
email:
  smtp_host: "smtp.qq.com"
  smtp_port: 587
  smtp_user: "your-qq@qq.com"
  smtp_password: "your-auth-code"  # QQ邮箱授权码
  from_name: "Suni AI"
  from_email: "your-qq@qq.com"
  use_tls: true
```

**获取 QQ 邮箱授权码：**
1. 登录 QQ 邮箱
2. 设置 → 账户 → 开启 SMTP 服务
3. 获取授权码（不是登录密码）

#### 163邮箱配置示例
```yaml
email:
  smtp_host: "smtp.163.com"
  smtp_port: 587
  smtp_user: "your-email@163.com"
  smtp_password: "your-auth-code"  # 163邮箱授权码
  from_name: "Suni AI"
  from_email: "your-email@163.com"
  use_tls: true
```

---

### 2. 验证码配置（可选调整）

```yaml
verification:
  code_length: 6                   # 验证码长度（默认6位）
  code_expire_minutes: 10          # 验证码有效期（默认10分钟）
  send_interval_seconds: 60        # 发送间隔（默认60秒）
  max_daily_per_email: 5           # 每个邮箱每天最大发送次数
  max_daily_per_ip: 10             # 每个IP每天最大发送次数
```

---

## 🧪 测试验证

### API 测试

1. **获取行为验证题目**
```bash
curl http://localhost:3000/api/captcha/challenge
```

2. **发送验证码**（需要先获取 captcha_token 和答题）
```bash
curl -X POST http://localhost:3000/api/verification/send \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "captcha_token": "your-token",
    "captcha_answer": "15"
  }'
```

3. **注册**（需要 verification_code）
```bash
curl -X POST http://localhost:3000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "verification_code": "ABC123"
  }'
```

---

## 🔒 安全特性

| 特性 | 说明 |
|------|------|
| 数学验证码 | 简单加减法，防机器人 |
| 验证码有效期 | 10分钟，过期失效 |
| 尝试次数限制 | 最多3次尝试验证 |
| 发送频率限制 | 60秒间隔，防刷 |
| 每日上限 | 每邮箱5次，每IP10次 |
| 验证码一次性 | 验证成功后立即失效 |

---

## 📝 邮件模板

验证码邮件包含：
- 美观的 HTML 模板
- 纯文本备用版本
- 6位字母数字验证码
- 有效期提示
- 安全提示信息

---

## 🐛 常见问题

### 邮件发送失败

**检查日志：**
```bash
# 查看错误信息
tail -f logs/suni.log | grep -i email
```

**常见原因：**
1. SMTP 密码/授权码错误
2. 邮箱未开启 SMTP 服务
3. 防火墙阻止 587/465 端口
4. 邮箱服务商限制

### 验证码收不到

1. 检查垃圾邮件文件夹
2. 确认邮箱地址正确
3. 检查发送频率限制
4. 查看后端日志

### 行为验证失败

1. 答案需要完全正确（不区分大小写）
2. 验证码5分钟有效
3. 刷新页面会重新生成题目

---

## 🚀 生产环境建议

1. **使用专业邮件服务**
   - SendGrid、Resend、Amazon SES
   - 送达率更高，有发送统计

2. **添加 Redis 缓存**
   - 多实例部署时需要共享验证码数据
   - 替换内存存储

3. **监控告警**
   - 监控发送失败率
   - 异常注册行为告警

4. **域名配置**
   - 配置 SPF、DKIM、DMARC
   - 提高邮件送达率
