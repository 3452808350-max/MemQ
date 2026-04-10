/**
 * 测试 ACP Client - 调用 Claude Code
 */

const { ACPClient, acp_call } = require('../dist/ACPClient');

async function main() {
  console.log('Testing ACP Client with Claude Code...\n');

  try {
    // 快速测试
    const result = await acp_call('claude', 'Hello, say "ACP test successful" in Chinese', {
      cwd: process.cwd(),
      timeout: 60,
    });

    console.log('Response:', result.text);
    console.log('Tool Calls:', result.toolCalls);
    console.log('\n✅ Test passed!');
  } catch (e) {
    console.error('❌ Test failed:', e.message);
    console.log('\nNote: This test requires Claude Code CLI installed.');
    console.log('Install: npm install -g @anthropic-ai/claude-code');
    process.exit(1);
  }
}

main();