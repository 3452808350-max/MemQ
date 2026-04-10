/**
 * 测试 Wire Client - 调用 Kimi CLI
 */

const { WireClient, wire_call } = require('../dist/WireClient');

async function main() {
  console.log('Testing Wire Client with Kimi CLI...\n');

  try {
    // 快速测试
    const result = await wire_call('Hello, say "Wire test successful" in Chinese', {
      cwd: process.cwd(),
      timeout: 60,
    });

    console.log('Response:', result.text);
    console.log('Status:', result.status);
    console.log('Events:', result.events.length);
    console.log('\n✅ Test passed!');
  } catch (e) {
    console.error('❌ Test failed:', e.message);
    console.log('\nNote: This test requires Kimi CLI installed.');
    console.log('Install: pip install kimi-code-cli or npm install -g kimi-code-cli');
    process.exit(1);
  }
}

main();