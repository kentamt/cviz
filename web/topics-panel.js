// topics-panel.js
import { Logger } from './geometry-renderer.js';

export class TopicsPanel {
    constructor(wsManager, options = {}) {
        this.wsManager = wsManager;
        this.options = {
            containerId: 'topics-panel',
            title: 'Topics',
            collapsed: false,
            ...options
        };

        this.topics = [];
        this.selectedTopics = new Set(wsManager ? Array.from(wsManager.desiredTopics || []) : []);

        this.createPanel();
        this.attachEvents();
    }

    createPanel() {
        this.container = document.createElement('div');
        this.container.id = this.options.containerId;
        this.container.style.position = 'fixed';
        this.container.style.top = '10px';
        this.container.style.right = '10px';
        this.container.style.width = '240px';
        this.container.style.maxHeight = '70vh';
        this.container.style.overflow = 'hidden';
        this.container.style.background = 'rgba(0, 0, 0, 0.8)';
        this.container.style.color = '#fff';
        this.container.style.fontFamily = 'monospace';
        this.container.style.fontSize = '12px';
        this.container.style.zIndex = '1002';
        this.container.style.border = '1px solid rgba(255,255,255,0.2)';
        this.container.style.borderRadius = '6px';
        this.container.style.boxShadow = '0 4px 12px rgba(0,0,0,0.25)';

        this.container.innerHTML = `
            <div id="${this.options.containerId}-header" style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.2);cursor:pointer;">
                <div>${this.options.title}</div>
                <button id="${this.options.containerId}-toggle" style="background:none;border:none;color:#fff;font-size:14px;cursor:pointer;">${this.options.collapsed ? '+' : '-'}</button>
            </div>
            <div id="${this.options.containerId}-body" style="display:${this.options.collapsed ? 'none' : 'block'};max-height:calc(70vh - 40px);overflow:auto;padding:6px 8px;"></div>
        `;

        document.body.appendChild(this.container);
        this.body = this.container.querySelector(`#${this.options.containerId}-body`);
    }

    attachEvents() {
        const header = this.container.querySelector(`#${this.options.containerId}-header`);
        const toggleBtn = this.container.querySelector(`#${this.options.containerId}-toggle`);

        header.addEventListener('click', (event) => {
            if (event.target !== toggleBtn) {
                this.toggleCollapse();
            }
        });
        toggleBtn.addEventListener('click', () => this.toggleCollapse());
    }

    toggleCollapse() {
        const body = this.body;
        const toggleBtn = this.container.querySelector(`#${this.options.containerId}-toggle`);
        const collapsed = body.style.display === 'none';
        body.style.display = collapsed ? 'block' : 'none';
        toggleBtn.textContent = collapsed ? '-' : '+';
    }

    setTopics(topics) {
        this.topics = topics;
        this.renderTopics();
    }

    updateSelection(topicsSet) {
        this.selectedTopics = new Set(topicsSet);
        this.syncCheckboxes();
    }

    renderTopics() {
        if (!this.body) return;

        if (!this.topics || this.topics.length === 0) {
            this.body.innerHTML = `<div style="padding:8px;color:rgba(255,255,255,0.6);">No topics detected</div>`;
            return;
        }

        const items = this.topics.map(topic => {
            const checked = this.selectedTopics.has(topic) ? 'checked' : '';
            return `
                <label style="display:flex;align-items:center;margin-bottom:4px;cursor:pointer;">
                    <input type="checkbox" data-topic="${topic}" ${checked} style="margin-right:6px;">
                    <span>${topic}</span>
                </label>
            `;
        }).join('');

        this.body.innerHTML = `
            <div style="max-height:calc(70vh - 60px);overflow:auto;">
                ${items}
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:6px;">
                <button id="${this.options.containerId}-all" style="flex:1;margin-right:4px;">All</button>
                <button id="${this.options.containerId}-none" style="flex:1;">None</button>
            </div>
        `;

        this.body.querySelectorAll('input[type="checkbox"]').forEach(input => {
            input.addEventListener('change', (e) => {
                const topic = e.target.dataset.topic;
                if (e.target.checked) {
                    this.selectedTopics.add(topic);
                } else {
                    this.selectedTopics.delete(topic);
                }
                this.pushSelection();
            });
        });

        this.body.querySelector(`#${this.options.containerId}-all`).addEventListener('click', () => {
            this.topics.forEach(topic => this.selectedTopics.add(topic));
            this.pushSelection();
            this.renderTopics();
        });

        this.body.querySelector(`#${this.options.containerId}-none`).addEventListener('click', () => {
            this.selectedTopics.clear();
            this.pushSelection();
            this.renderTopics();
        });
    }

    syncCheckboxes() {
        if (!this.body) return;
        this.body.querySelectorAll('input[type="checkbox"]').forEach(input => {
            const topic = input.dataset.topic;
            input.checked = this.selectedTopics.has(topic);
        });
    }

    pushSelection() {
        if (!this.wsManager) return;

        const topicsArray = Array.from(this.selectedTopics);
        Logger.log(`Updating topics selection: ${topicsArray.join(', ')}`);
        this.wsManager.setTopics(topicsArray);
    }
}
