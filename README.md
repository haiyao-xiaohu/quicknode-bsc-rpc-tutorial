# QuickNode BSC RPC 接入与检测教程

用 Python 3 检查 QuickNode 的 BNB Smart Chain（BSC）HTTP RPC：连接是否成功、网络是否正确、区块是否更新、最新块是否新鲜，以及单次请求耗时。

不需要钱包、私钥或链上资金。脚本只发送 5 次只读请求，不签名、不广播交易，且不依赖第三方 Python 包。

## 1. 在 QuickNode 获取 BSC endpoint

1. 登录自己的 QuickNode Dashboard。
2. 进入 **Infrastructure → Endpoints → New Endpoint**。
3. 选择 **BNB Smart Chain → Mainnet**，按后台提示完成创建。套餐、价格与确认步骤以账户页面为准。
4. 打开 endpoint 的 **Overview**，复制 **HTTP URL**。本教程不使用 WSS URL。

完整 endpoint 中的主机名和 token 都不要出现在公开代码、截图或录屏里。复制动作在录屏外完成，随后在终端隐藏粘贴。

## 2. 下载并检查环境

下载本仓库代码并进入解压目录，或者在 GitHub 点击 **Code** 复制仓库地址后执行 `git clone`。

```bash
python3 --version
```

需要 Python 3.9 或更高版本。Windows 可把以下命令中的 `python3` 替换为 `py -3`。私人 endpoint 模式应在支持隐藏输入的交互式终端中运行。

## 3. 先试公开演示节点

```bash
python3 check_rpc.py --demo
```

`--demo` 使用 QuickNode 官方文档里的公开演示地址 `https://docs-demo.bsc.quiknode.pro/`。不需要提供私人 token，适合教学；它的可用性和限制可能变化，不作为生产服务依赖。

## 4. 检测自己的 QuickNode endpoint

```bash
python3 check_rpc.py
```

屏幕会出现以下提示：

```text
粘贴 QuickNode HTTPS 地址（隐藏输入）:
```

粘贴完整 HTTP endpoint 并按回车。输入时不会显示字符，脚本会显示 `Endpoint: [已隐藏]`。不要把地址直接写进 shell 命令，避免进入命令历史。

终端不支持隐藏输入时，脚本会停止；不会改用明文输入。录屏工具也不要开启按键显示或剪贴板展示。

## 5. 理解检测结果

| 检测 | 请求方法 | 如何判断 |
| --- | --- | --- |
| 网络 | `eth_chainId` | BSC 主网为 `0x38`，十进制 56；测试网为 `0x61`，十进制 97 |
| 区块更新 | `eth_blockNumber`，间隔 5 秒调用两次 | 转成十进制后比较，高度应增长；不增长时稍后复查 |
| 同步状态 | `eth_syncing` | `false` 表示未报告正在同步；对象表示正在同步 |
| 新鲜度 | `eth_getBlockByNumber`，参数 `["latest", false]` | 用最新块 timestamp 对比本机时间，需要本机时钟准确 |
| 耗时 | 每次请求的 `elapsed_ms` | 包含网络、TLS 和服务处理，是单次端到端采样 |

HTTP 200 仍可能携带 JSON-RPC `error`，不能仅凭 HTTP 状态判断成功。脚本检查响应格式、请求 ID、错误字段与结果类型。

以下为示例，数值不是你的节点测试结果：

```text
Endpoint: [已隐藏]
{"method": "eth_chainId", "http": 200, "result": "0x38", "elapsed_ms": 300}
链 ID: 56 / BSC 主网
...
区块增长: 10
最新块距本机时间（秒）: 1.0
基础只读检测通过
```

脚本判定“基础只读检测通过”需要：链 ID 为 56、区块增长、同步状态为 false、所有请求成功，最新块距本机时间在 -5～30 秒之间。这个时间范围是教程采用的复查阈值，**不是 QuickNode 的官方 SLA**。

`eth_syncing=false` 不能单独证明节点已经追上最新区块；高度增长也不能排除节点整体落后。需要结合区块时间，必要时与其他可信来源比较。

## 6. 保存经过字段筛选的报告

```bash
python3 check_rpc.py --report report.json
# 或者保存公开演示检测结果
python3 check_rpc.py --demo --report report.json
```

报告包含方法、状态码、耗时、链 ID、区块高度、区块时间和检测结论。不会保存 endpoint、token、原始响应、原始错误消息或钱包数据。报告默认被 `.gitignore` 排除；分享前仍应检查其内容。

程序退出码为 0 表示基础检测通过；1 表示需要复查或发生错误；130 表示取消。

## 7. 常见问题

| 现象 | 排查方向 |
| --- | --- |
| HTTP 401 / 403 | 地址是否完整、token 是否有效、IP/来源/方法等访问限制 |
| HTTP 429 | 请求速率、套餐配额；降低频率并检查后台限制 |
| JSON-RPC error | 方法名称、参数、网络与套餐功能支持 |
| 连接失败或超时 | 网络、DNS、代理、HTTPS endpoint 是否正确 |
| 链 ID 为其他值 | 创建或复制了其他网络的 endpoint |
| 高度不增长、块时间明显落后 | 等待后复查，与可信来源对比，检查节点状态 |

默认使用本机代理配置。只有确定需要绕过代理时，才运行：

```bash
python3 check_rpc.py --demo --direct
```

不要为排查连接问题关闭 TLS 证书校验。

## 8. 接入项目与录屏流程

基础检测通过后，在项目的服务端配置或密钥管理中设置 endpoint，避免提交真实 `.env`。浏览器前端里的 endpoint 能被访问者查看；按业务需要使用服务端转发或 QuickNode 的访问限制，并单独验证浏览器 CORS。

根据项目实际需求继续检测 `eth_call`、`eth_getLogs`、历史区块、WSS 订阅等。此次 HTTP 只读检测不证明交易广播或所有业务功能均可用，也不是压力测试。

录屏建议顺序：介绍目标 → 后台创建步骤的文字说明 → 公开演示命令 → 私人地址隐藏输入说明 → 链 ID → 区块增长 → 同步与新鲜度 → 耗时 → 错误排查。

录制一个干净的终端窗口，使用通用提示符，隐藏用户名与本地目录；关闭通知、账户头像和按键展示。不要录制私人 QuickNode 后台的 endpoint、账单、邮箱或账号信息。需要展示后台时，使用演示账户和打码画面。

## 9. 本地验证代码

```bash
python3 -m unittest -v
```

测试使用模拟响应，不连接网络，检查正常流程以及 HTTP、RPC、连接异常中的 endpoint 信息不会被打印或保存。

## 官方资料

- [QuickNode BSC QuickStart](https://www.quicknode.com/docs/bnb-smart-chain/quickstart)
- [QuickNode eth_blockNumber](https://www.quicknode.com/docs/bnb-smart-chain/eth_blockNumber)
- [QuickNode Dashboard 使用说明](https://www.quicknode.com/guides/quicknode-products/how-to-use-the-quicknode-dashboard)
- [BNB Chain RPC 与网络 ID](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/)

本项目为独立教学示例，不是 QuickNode 官方项目。
