#!/usr/bin/env python3
"""Read-only BSC checks. Never prints or stores the endpoint or raw errors."""
import argparse
import getpass
import json
import sys
import time
import urllib.request
import urllib.error
import warnings
from urllib.parse import urlsplit
from datetime import datetime, timezone

PUBLIC_DEMO = 'https://docs-demo.bsc.quiknode.pro/'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo', action='store_true', help='QuickNode official public demo endpoint')
    p.add_argument('--direct', action='store_true', help='Bypass local HTTP proxy settings')
    p.add_argument('--report', help='Save a sanitized JSON report')
    args = p.parse_args()
    if not args.demo and not sys.stdin.isatty():
        print('私人 endpoint 必须在交互式终端中隐藏输入；请直接运行 python3 check_rpc.py。')
        return 1
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            endpoint = PUBLIC_DEMO if args.demo else getpass.getpass('粘贴 QuickNode HTTPS 地址（隐藏输入）: ')
        except getpass.GetPassWarning:
            print('终端无法隐藏输入，请换用支持隐藏输入的交互式终端。')
            return 1
    try:
        parsed = urlsplit(endpoint)
    except ValueError:
        print('HTTPS endpoint 格式无效，地址不会显示。')
        return 1
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        print('请输入有效 HTTPS endpoint。地址不会显示。')
        return 1
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if args.direct else urllib.request.build_opener()
    records = []
    print('Endpoint: QuickNode 官方公共演示' if args.demo else 'Endpoint: [已隐藏]')
    def rpc(method, params):
        payload = {'jsonrpc': '2.0', 'id': len(records) + 1, 'method': method, 'params': params}
        start = time.perf_counter()
        record = {'method': method}
        try:
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with opener.open(req, timeout=15) as response:
                record['http'] = response.status
                data = json.load(response)
            if not isinstance(data, dict) or data.get('jsonrpc') != '2.0' or data.get('id') != payload['id']:
                raise ValueError('invalid envelope')
            if 'error' in data:
                error = data['error']
                record['error'] = 'JSON-RPC error'
                if isinstance(error, dict) and isinstance(error.get('code'), int):
                    record['code'] = error['code']
                result = None
            elif 'result' in data:
                result = data['result']
                if method in ('eth_chainId', 'eth_blockNumber'):
                    if not isinstance(result, str) or not result.startswith('0x'):
                        raise ValueError('invalid hex')
                    int(result, 16)
                    record['result'] = result
                elif method == 'eth_syncing':
                    if result is False:
                        record['result'] = False
                    elif isinstance(result, dict):
                        record['result'] = 'syncing'
                    else:
                        raise ValueError('invalid syncing result')
                elif method == 'eth_getBlockByNumber':
                    if not isinstance(result, dict):
                        raise ValueError('missing block')
                    record['result'] = {key: hex(int(result[key], 16)) for key in ('number', 'timestamp')}
                    result = record['result']
            else:
                raise ValueError('missing result')
        except urllib.error.HTTPError as e:
            record.update(http=e.code, error='HTTP error')
            result = None
        except (urllib.error.URLError, TimeoutError, OSError):
            record['error'] = '连接失败或超时，请检查网络、代理与 endpoint'
            result = None
        except (ValueError, KeyError, TypeError):
            record['error'] = '响应格式不符合预期'
            result = None
        record['elapsed_ms'] = round((time.perf_counter() - start) * 1000)
        records.append(record)
        print(json.dumps(record, ensure_ascii=False))
        return result
    chain = rpc('eth_chainId', [])
    correct_chain = chain is not None and int(chain, 16) == 56
    print('链 ID: 56 / BSC 主网' if correct_chain else '链 ID 检测失败或不是 BSC 主网')
    h1 = rpc('eth_blockNumber', [])
    print('等待 5 秒，再检查区块高度…')
    time.sleep(5)
    h2 = rpc('eth_blockNumber', [])
    delta = int(h2, 16) - int(h1, 16) if h1 and h2 else None
    print('区块增长: ' + str(delta))
    sync = rpc('eth_syncing', [])
    block = rpc('eth_getBlockByNumber', ['latest', False])
    age = round(time.time() - int(block['timestamp'], 16), 1) if block else None
    print('最新块距本机时间（秒）: ' + str(age))
    print('eth_syncing=false 仅表示节点未报告正在同步，不能单独证明数据最新。')
    print('耗时为单次端到端采样，不是性能压测。区块不增长时请稍后复查并对比其他来源。')
    passed = correct_chain and delta is not None and delta > 0 and sync is False and age is not None and -5 <= age <= 30 and not any('error' in r for r in records)
    verdict = '基础只读检测通过' if passed else '需要复查：网络、链 ID、同步状态或区块新鲜度'
    print(verdict)
    print('这里只验证只读 HTTP RPC；项目还需单独验证 eth_call、日志、WSS 或历史数据等实际需求。')
    if args.report:
        report = {'source': 'QuickNode public docs demo' if args.demo else 'private endpoint [redacted]', 'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'records': records, 'block_growth': delta, 'block_age_seconds': age, 'verdict': verdict}
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    return 0 if passed else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\n检测取消。')
        sys.exit(130)
    except Exception:
        print('检测未完成，请检查终端、地址格式、响应及报告文件权限。为保护 endpoint，不显示原始异常。')
        sys.exit(1)
