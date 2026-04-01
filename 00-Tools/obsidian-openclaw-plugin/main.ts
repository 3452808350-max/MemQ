import {
	App,
	Plugin,
	PluginSettingTab,
	Setting,
	WorkspaceLeaf,
	ItemView,
	TFile,
	TFolder,
	Notice,
	MarkdownView
} from "obsidian";

// View type constant
const VIEW_TYPE_OPENCLAW = "openclaw-chat-view";

// Plugin settings interface
interface OpenClawSettings {
	gatewayUrl: string;
	apiKeyPath: string;
	chatFolder: string;
	autoSaveChats: boolean;
}

// Default settings
const DEFAULT_SETTINGS: OpenClawSettings = {
	gatewayUrl: "ws://106.53.186.90:8080",
	apiKeyPath: "~/文档/openclaw-api-key.txt",
	chatFolder: "ClawChats",
	autoSaveChats: false
};

// Message type for chat
interface ChatMessage {
	role: "user" | "assistant" | "system";
	content: string;
	timestamp: number;
}

// OpenClaw Chat View
class OpenClawChatView extends ItemView {
	plugin: OpenClawPlugin;
	messages: ChatMessage[] = [];
	ws: WebSocket | null = null;
	messageContainer: HTMLElement | null = null;
	inputEl: HTMLTextAreaElement | null = null;
	isConnected = false;

	constructor(leaf: WorkspaceLeaf, plugin: OpenClawPlugin) {
		super(leaf);
		this.plugin = plugin;
	}

	getViewType(): string {
		return VIEW_TYPE_OPENCLAW;
	}

	getDisplayText(): string {
		return "OpenClaw Chat";
	}

	getIcon(): string {
		return "message-circle";
	}

	async onOpen(): Promise<void> {
		const container = this.containerEl.children[1];
		container.empty();
		container.addClass("openclaw-chat-container");

		// Header
		const header = container.createDiv({ cls: "openclaw-header" });
		header.createEl("h3", { text: "🐾 OpenClaw" });
		const statusIndicator = header.createSpan({ cls: "openclaw-status" });
		statusIndicator.textContent = "●";

		// Connection controls
		const controls = container.createDiv({ cls: "openclaw-controls" });
		const connectBtn = controls.createEl("button", { text: "连接", cls: "mod-cta" });
		const disconnectBtn = controls.createEl("button", { text: "断开" });
		const saveBtn = controls.createEl("button", { text: "保存对话" });
		const tagBtn = controls.createEl("button", { text: "AI标签" });

		// Messages container
		this.messageContainer = container.createDiv({ cls: "openclaw-messages" });

		// Input area
		const inputArea = container.createDiv({ cls: "openclaw-input-area" });
		this.inputEl = inputArea.createEl("textarea", {
			cls: "openclaw-input",
			placeholder: "输入消息... (Shift+Enter 发送)"
		});
		const sendBtn = inputArea.createEl("button", { text: "发送", cls: "mod-cta" });

		// Event listeners
		connectBtn.addEventListener("click", () => this.connect(statusIndicator));
		disconnectBtn.addEventListener("click", () => this.disconnect(statusIndicator));
		saveBtn.addEventListener("click", () => this.saveChat());
		tagBtn.addEventListener("click", () => this.generateTags());
		sendBtn.addEventListener("click", () => this.sendMessage());
		
		this.inputEl.addEventListener("keydown", (e) => {
			if (e.key === "Enter" && e.shiftKey) {
				e.preventDefault();
				this.sendMessage();
			}
		});

		// Auto-connect if settings allow
		if (this.plugin.settings.autoSaveChats) {
			this.connect(statusIndicator);
		}
	}

	async onClose(): Promise<void> {
		this.disconnect();
	}

	connect(statusEl: HTMLElement): void {
		if (this.ws?.readyState === WebSocket.OPEN) {
			new Notice("已经连接");
			return;
		}

		try {
			this.ws = new WebSocket(this.plugin.settings.gatewayUrl);
			
			this.ws.onopen = () => {
				this.isConnected = true;
				statusEl.addClass("connected");
				new Notice("已连接到 OpenClaw");
				
				// Send auth if needed
				const apiKey = this.plugin.getApiKey();
				if (apiKey) {
					this.ws?.send(JSON.stringify({
						type: "auth",
						token: apiKey
					}));
				}
			};

			this.ws.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data);
					this.handleMessage(data);
				} catch (e) {
					// Plain text message
					this.addMessage({
						role: "assistant",
						content: event.data,
						timestamp: Date.now()
					});
				}
			};

			this.ws.onerror = (error) => {
				console.error("WebSocket error:", error);
				new Notice("连接错误，请检查 Gateway 地址");
			};

			this.ws.onclose = () => {
				this.isConnected = false;
				statusEl.removeClass("connected");
				new Notice("连接已断开");
			};

		} catch (error) {
			new Notice("连接失败: " + error.message);
		}
	}

	disconnect(statusEl?: HTMLElement): void {
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
		this.isConnected = false;
		if (statusEl) {
			statusEl.removeClass("connected");
		}
	}

	handleMessage(data: any): void {
		if (data.type === "message" || data.content) {
			this.addMessage({
				role: "assistant",
				content: data.content || data.message,
				timestamp: Date.now()
			});
		} else if (data.type === "error") {
			new Notice("错误: " + data.message);
		}
	}

	sendMessage(): void {
		if (!this.inputEl || !this.isConnected) {
			new Notice("请先连接 OpenClaw");
			return;
		}

		const content = this.inputEl.value.trim();
		if (!content) return;

		// Add user message
		this.addMessage({
			role: "user",
			content,
			timestamp: Date.now()
		});

		// Send to server
		this.ws?.send(JSON.stringify({
			type: "message",
			content,
			timestamp: Date.now()
		}));

		// Clear input
		this.inputEl.value = "";
	}

	addMessage(msg: ChatMessage): void {
		this.messages.push(msg);
		
		if (!this.messageContainer) return;

		const msgEl = this.messageContainer.createDiv({
			cls: `openclaw-message ${msg.role}`
		});

		const header = msgEl.createDiv({ cls: "message-header" });
		header.createSpan({ cls: "role", text: msg.role === "user" ? "你" : "OpenClaw" });
		header.createSpan({ 
			cls: "time", 
			text: new Date(msg.timestamp).toLocaleTimeString() 
		});

		const content = msgEl.createDiv({ cls: "message-content" });
		content.innerHTML = this.formatMessage(msg.content);

		// Scroll to bottom
		this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
	}

	formatMessage(content: string): string {
		// Simple markdown formatting
		return content
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
			.replace(/`([^`]+)`/g, "<code>$1</code>")
			.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
			.replace(/\*([^*]+)\*/g, "<em>$1</em>")
			.replace(/\n/g, "<br>");
	}

	async saveChat(): Promise<void> {
		if (this.messages.length === 0) {
			new Notice("没有对话可保存");
			return;
		}

		const date = new Date().toISOString().split("T")[0];
		const folderPath = this.plugin.settings.chatFolder;
		const fileName = `${folderPath}/${date}.md`;

		// Ensure folder exists
		await this.plugin.ensureFolder(folderPath);

		// Build content
		let content = `# OpenClaw 对话 - ${date}\n\n`;
		for (const msg of this.messages) {
			const time = new Date(msg.timestamp).toLocaleString();
			content += `**${msg.role === "user" ? "我" : "OpenClaw"}** (${time}):\n${msg.content}\n\n---\n\n`;
		}

		// Create or append
		const existingFile = this.app.vault.getAbstractFileByPath(fileName);
		if (existingFile instanceof TFile) {
			const existing = await this.app.vault.read(existingFile);
			content = existing + "\n\n" + content;
			await this.app.vault.modify(existingFile, content);
		} else {
			await this.app.vault.create(fileName, content);
		}

		new Notice(`对话已保存到 ${fileName}`);
	}

	async generateTags(): Promise<void> {
		const activeFile = this.app.workspace.getActiveFile();
		if (!activeFile) {
			new Notice("请先打开一个笔记文件");
			return;
		}

		if (!this.isConnected) {
			new Notice("请先连接 OpenClaw");
			return;
		}

		// Read current file content
		const content = await this.app.vault.read(activeFile);
		
		// Send to OpenClaw for tagging
		this.ws?.send(JSON.stringify({
			type: "tag_request",
			content: content,
			filename: activeFile.name
		}));

		new Notice("已发送标签请求到 OpenClaw");
	}
}

// Settings Tab
class OpenClawSettingTab extends PluginSettingTab {
	plugin: OpenClawPlugin;

	constructor(app: App, plugin: OpenClawPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl("h2", { text: "OpenClaw Chat 设置" });

		// Gateway URL
		new Setting(containerEl)
			.setName("Gateway 地址")
			.setDesc("OpenClaw WebSocket 网关地址 (默认: ws://106.53.186.90:8080)")
			.addText((text) =>
				text
					.setPlaceholder("ws://106.53.186.90:8080")
					.setValue(this.plugin.settings.gatewayUrl)
					.onChange(async (value) => {
						this.plugin.settings.gatewayUrl = value;
						await this.plugin.saveSettings();
					})
			);

		// API Key Path
		new Setting(containerEl)
			.setName("API Key 文件路径")
			.setDesc("存储 API Key 的文件路径 (支持 ~ 表示家目录)")
			.addText((text) =>
				text
					.setPlaceholder("~/文档/openclaw-api-key.txt")
					.setValue(this.plugin.settings.apiKeyPath)
					.onChange(async (value) => {
						this.plugin.settings.apiKeyPath = value;
						await this.plugin.saveSettings();
					})
			);

		// Chat Folder
		new Setting(containerEl)
			.setName("聊天记录文件夹")
			.setDesc("保存聊天记录的文件夹路径")
			.addText((text) =>
				text
					.setPlaceholder("ClawChats")
					.setValue(this.plugin.settings.chatFolder)
					.onChange(async (value) => {
						this.plugin.settings.chatFolder = value;
						await this.plugin.saveSettings();
					})
			);

		// Auto Save
		new Setting(containerEl)
			.setName("自动保存对话")
			.setDesc("每次对话后自动保存到文件")
			.addToggle((toggle) =>
				toggle
					.setValue(this.plugin.settings.autoSaveChats)
					.onChange(async (value) => {
						this.plugin.settings.autoSaveChats = value;
						await this.plugin.saveSettings();
					})
			);
	}
}

// Main Plugin Class
export default class OpenClawPlugin extends Plugin {
	settings: OpenClawSettings;
	view: OpenClawChatView | null = null;

	async onload(): Promise<void> {
		await this.loadSettings();

		// Register view
		this.registerView(
			VIEW_TYPE_OPENCLAW,
			(leaf) => {
				this.view = new OpenClawChatView(leaf, this);
				return this.view;
			}
		);

		// Add ribbon icon
		this.addRibbonIcon("message-circle", "OpenClaw Chat", () => {
			this.activateView();
		});

		// Add command
		this.addCommand({
			id: "open-openclaw-chat",
			name: "打开 OpenClaw 聊天",
			callback: () => {
				this.activateView();
			}
		});

		// Add settings tab
		this.addSettingTab(new OpenClawSettingTab(this.app, this));
	}

	onunload(): void {
		if (this.view) {
			this.view.disconnect();
		}
	}

	async loadSettings(): Promise<void> {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings(): Promise<void> {
		await this.saveData(this.settings);
	}

	async activateView(): Promise<void> {
		const { workspace } = this.app;

		let leaf: WorkspaceLeaf | null = null;
		const leaves = workspace.getLeavesOfType(VIEW_TYPE_OPENCLAW);

		if (leaves.length > 0) {
			leaf = leaves[0];
		} else {
			leaf = workspace.getRightLeaf(false);
			await leaf?.setViewState({ type: VIEW_TYPE_OPENCLAW, active: true });
		}

		if (leaf) {
			workspace.revealLeaf(leaf);
		}
	}

	getApiKey(): string | null {
		// Expand ~ to home directory
		const path = this.settings.apiKeyPath.replace(/^~/, process.env.HOME || "");
		try {
			const fs = require("fs");
			return fs.readFileSync(path, "utf8").trim();
		} catch (e) {
			console.error("Failed to read API key:", e);
			return null;
		}
	}

	async ensureFolder(path: string): Promise<void> {
		const folder = this.app.vault.getAbstractFileByPath(path);
		if (!folder) {
			await this.app.vault.createFolder(path);
		}
	}
}
	