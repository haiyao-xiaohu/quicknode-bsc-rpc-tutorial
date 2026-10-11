import contextlib
import io
import json
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import check_rpc

SECRET = 'https://private-example.bsc.quiknode.pro/DO_NOT_PUBLISH_TOKEN/'

class Response(io.StringIO):
    status = 200

class FakeOpener:
    def __init__(self, failure=None, wrong_chain=False):
        self.index = 0
        self.failure = failure
        self.wrong_chain = wrong_chain

    def open(self, req, timeout):
        if self.failure:
            if isinstance(self.failure, Exception):
                raise self.failure
            self.index += 1
            return Response(json.dumps({'jsonrpc': '2.0', 'id': self.index, 'error': {'code': -32601, 'message': SECRET}}))
        self.index += 1
        results = ['0x1' if self.wrong_chain else '0x38', '0x100', '0x110', False, {'number': '0x111', 'timestamp': hex(int(time.time())), 'private_field': SECRET}]
        return Response(json.dumps({'jsonrpc': '2.0', 'id': self.index, 'result': results[self.index - 1]}))

class PrivacyTests(unittest.TestCase):
    def run_check(self, opener):
        with tempfile.TemporaryDirectory() as temp:
            report_path = Path(temp) / 'report.json'
            output = io.StringIO()
            with patch('sys.argv', ['check_rpc.py', '--report', str(report_path)]), patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', return_value=SECRET), patch('urllib.request.build_opener', return_value=opener), patch('time.sleep'), contextlib.redirect_stdout(output):
                status = check_rpc.main()
            raw = report_path.read_text()
            for text in (output.getvalue(), raw):
                self.assertNotIn(SECRET, text)
                self.assertNotIn('DO_NOT_PUBLISH_TOKEN', text)
                self.assertNotIn('private-example', text)
                self.assertNotIn('private_field', text)
            return status, json.loads(raw)

    def test_success_filters_block_fields(self):
        status, report = self.run_check(FakeOpener())
        self.assertEqual(status, 0)
        self.assertEqual(report['block_growth'], 16)
        self.assertEqual(set(report['records'][-1]['result']), {'number', 'timestamp'})

    def test_wrong_chain_fails(self):
        status, _ = self.run_check(FakeOpener(wrong_chain=True))
        self.assertEqual(status, 1)

    def test_rpc_error_message_not_disclosed(self):
        status, report = self.run_check(FakeOpener(failure='rpc'))
        self.assertEqual(status, 1)
        self.assertEqual(report['records'][0]['code'], -32601)

    def test_http_error_url_and_body_not_disclosed(self):
        error = urllib.error.HTTPError(SECRET, 403, SECRET, {}, io.BytesIO(SECRET.encode()))
        status, report = self.run_check(FakeOpener(failure=error))
        self.assertEqual(status, 1)
        self.assertEqual(report['records'][0]['http'], 403)

    def test_connection_error_not_disclosed(self):
        status, _ = self.run_check(FakeOpener(failure=urllib.error.URLError(SECRET)))
        self.assertEqual(status, 1)

    def test_noninteractive_private_mode_refused(self):
        with patch('sys.argv', ['check_rpc.py']), patch('sys.stdin.isatty', return_value=False), patch('getpass.getpass') as prompt, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_rpc.main(), 1)
            prompt.assert_not_called()

if __name__ == '__main__':
    unittest.main()
