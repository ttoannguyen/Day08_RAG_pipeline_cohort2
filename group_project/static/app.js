document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatFeed = document.getElementById("chat-feed");
    const btnReset = document.getElementById("btn-reset");
    
    // Conversation history memory array
    let chatHistory = [];

    // Prompt Inspector DOM Elements
    const DEFAULT_SYSTEM_PROMPT = `Answer the question in Vietnamese.

If the question is a general greeting (e.g., "xin chào", "hello", "hi") or asking about your identity (e.g., "bạn là ai", "tên gì"), reply politely directly as the DrugLaw RAG Assistant.

For all other questions concerning drug laws, legal documents, or celebrity news:
- Only use information from the provided context.
- For every statement of fact or claim, immediately insert a citation in brackets linking to the specific source (e.g., [Luật Phòng chống ma tuý 2021, Điều 3] or [VnExpress, 2024]).
- If the information is not explicitly stated in the provided context, state 'Tôi không thể xác minh thông tin này từ nguồn hiện có' rather than guessing.
- Structure your answer with clear paragraphs.`;

    const promptSystemEditor = document.getElementById("prompt-system-editor");
    const promptUserViewer = document.getElementById("prompt-user-viewer");
    const btnResetPrompt = document.getElementById("btn-reset-prompt");

    if (promptSystemEditor) {
        promptSystemEditor.value = DEFAULT_SYSTEM_PROMPT;
    }

    if (btnResetPrompt && promptSystemEditor) {
        btnResetPrompt.addEventListener("click", () => {
            promptSystemEditor.value = DEFAULT_SYSTEM_PROMPT;
        });
    }
    
    // Sliders & Badge Indicators
    const paramTopK = document.getElementById("param-top-k");
    const valTopK = document.getElementById("val-top-k");
    const paramThreshold = document.getElementById("param-threshold");
    const valThreshold = document.getElementById("val-threshold");
    const paramTemp = document.getElementById("param-temp");
    const valTemp = document.getElementById("val-temp");
    
    // Modal DOM Elements
    const docModal = document.getElementById("doc-modal");
    const modalTitle = document.getElementById("modal-title");
    const modalBodyMeta = document.getElementById("modal-body-meta");
    const modalBody = document.getElementById("modal-body");
    const modalClose = document.getElementById("modal-close");
    
    // Theme toggle DOM Elements
    const btnThemeToggle = document.getElementById("btn-theme-toggle");
    
    // Create floating citation tooltip element dynamically
    const citationTooltip = document.createElement("div");
    citationTooltip.className = "citation-tooltip glass";
    document.body.appendChild(citationTooltip);
    
    // Config items
    const paramUseRerank = document.getElementById("param-use-reranking");
    const paramRerankMethod = document.getElementById("param-rerank-method");
    const paramLlmModel = document.getElementById("param-llm-model");
    
    // Sidebar Collapse Elements
    const sidebar = document.getElementById("sidebar");
    const btnCollapseSidebar = document.getElementById("btn-collapse-sidebar");
    const btnExpandSidebar = document.getElementById("btn-expand-sidebar");
    
    // Splitter dragging elements
    const dragHandle = document.getElementById("drag-handle");
    const chatSection = document.getElementById("chat-section");
    const inspectorSection = document.getElementById("inspector-section");
    
    // Inspector elements
    const statusPanelGrid = document.getElementById("status-panel-grid");
    const statusLatency = document.getElementById("status-latency");
    const fallbackCard = document.getElementById("fallback-card");
    const statusFallback = document.getElementById("status-fallback");
    const pipelineMeta = document.getElementById("pipeline-meta");
    
    // Tab Panes
    const listLexical = document.getElementById("list-lexical");
    const listSemantic = document.getElementById("list-semantic");
    const listReranked = document.getElementById("list-reranked");
    const listSources = document.getElementById("list-sources");

    // =============================================================================
    // SIDEBAR COLLAPSE FUNCTIONALITY
    // =============================================================================
    btnCollapseSidebar.addEventListener("click", () => {
        sidebar.classList.add("collapsed");
        btnExpandSidebar.style.display = "flex";
    });

    btnExpandSidebar.addEventListener("click", () => {
        sidebar.classList.remove("collapsed");
        btnExpandSidebar.style.display = "none";
    });

    // =============================================================================
    // DRAGGABLE SPLITTER (RESIZER)
    // =============================================================================
    let isDragging = false;

    dragHandle.addEventListener("mousedown", (e) => {
        isDragging = true;
        dragHandle.classList.add("dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none"; // Prevent text selection
    });

    document.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        
        const mainContent = document.querySelector(".main-content");
        const containerRect = mainContent.getBoundingClientRect();
        
        // Calculate relative mouse X position within the main content container
        const leftPos = e.clientX - containerRect.left;
        const percentage = (leftPos / containerRect.width) * 100;
        
        // Apply boundaries (30% to 80%)
        if (percentage >= 25 && percentage <= 80) {
            chatSection.style.flex = `0 0 ${percentage}%`;
            inspectorSection.style.flex = `0 0 ${100 - percentage}%`;
        }
    });

    document.addEventListener("mouseup", () => {
        if (isDragging) {
            isDragging = false;
            dragHandle.classList.remove("dragging");
            document.body.style.cursor = "default";
            document.body.style.userSelect = "auto";
        }
    });

    // =============================================================================
    // PARAMETERS LISTENERS
    // =============================================================================
    paramTopK.addEventListener("input", (e) => {
        valTopK.textContent = e.target.value;
    });

    paramThreshold.addEventListener("input", (e) => {
        valThreshold.textContent = parseFloat(e.target.value).toFixed(2);
    });

    paramTemp.addEventListener("input", (e) => {
        valTemp.textContent = parseFloat(e.target.value).toFixed(1);
    });

    paramUseRerank.addEventListener("change", (e) => {
        paramRerankMethod.disabled = !e.target.checked;
    });

    // =============================================================================
    // THEME TOGGLE EVENT HANDLER
    // =============================================================================
    btnThemeToggle.addEventListener("click", () => {
        const body = document.body;
        body.classList.toggle("light-theme");
        
        const icon = btnThemeToggle.querySelector(".theme-icon");
        if (body.classList.contains("light-theme")) {
            icon.className = "fa-solid fa-moon theme-icon";
            localStorage.setItem("theme", "light");
        } else {
            icon.className = "fa-solid fa-sun theme-icon";
            localStorage.setItem("theme", "dark");
        }
    });

    // Load stored theme on load
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
        document.body.classList.add("light-theme");
        btnThemeToggle.querySelector(".theme-icon").className = "fa-solid fa-moon theme-icon";
    }

    // =============================================================================
    // TABS CONTROLLER
    // =============================================================================
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
        });
    });

    function switchTab(tabId) {
        tabButtons.forEach(b => {
            if (b.getAttribute("data-tab") === tabId) {
                b.classList.add("active");
            } else {
                b.classList.remove("active");
            }
        });
        tabPanes.forEach(p => {
            if (p.getAttribute("id") === tabId) {
                p.classList.add("active");
            } else {
                p.classList.remove("active");
            }
        });
    }

    // =============================================================================
    // CHAT SUGGESTIONS
    // =============================================================================
    const suggestionBtns = document.querySelectorAll(".suggestion-btn");
    suggestionBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const query = btn.getAttribute("data-query");
            submitQuery(query);
        });
    });

    // =============================================================================
    // FORMAT RESPONSE WITH MARKDOWN & CITATION BADGES
    // =============================================================================
    function formatMessageText(text) {
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,
                gfm: true
            });
            // Parse markdown using marked.parse
            let parsed = marked.parse(text);
            
            // Replace brackets with custom clickable citation badges in the parsed HTML
            parsed = parsed.replace(/\[([^\]]+)\]/g, (match, citeText) => {
                const meta = getChunkMetadataByCitation(citeText);
                const url = meta && meta.url ? meta.url : "";
                if (url) {
                    return `<span class="citation-badge" data-cite-target="${citeText}">${citeText}</span><a href="${url}" target="_blank" class="citation-link" title="Mở liên kết nguồn"><i class="fa-solid fa-arrow-up-right-from-square" style="margin-right: 3px;"></i>nguồn</a>`;
                }
                return `<span class="citation-badge" data-cite-target="${citeText}">${citeText}</span>`;
            });
            return parsed;
        } else {
            // Escape HTML to prevent XSS as fallback
            let escaped = text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");

            // Convert double asterisks to bold
            escaped = escaped.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

            // Convert newlines to breaks
            escaped = escaped.replace(/\n/g, "<br>");

            // Replace brackets with custom clickable citation badges
            escaped = escaped.replace(/\[([^\]]+)\]/g, (match, citeText) => {
                const meta = getChunkMetadataByCitation(citeText);
                const url = meta && meta.url ? meta.url : "";
                if (url) {
                    return `<span class="citation-badge" data-cite-target="${citeText}">${citeText}</span><a href="${url}" target="_blank" class="citation-link" title="Mở liên kết nguồn"><i class="fa-solid fa-arrow-up-right-from-square" style="margin-right: 3px;"></i>nguồn</a>`;
                }
                return `<span class="citation-badge" data-cite-target="${citeText}">${citeText}</span>`;
            });

            return escaped;
        }
    }

    // =============================================================================
    // CHAT ACTIONS (STREAMING SUPPORT)
    // =============================================================================
    function appendUserMessage(text) {
        const messageDiv = document.createElement("div");
        messageDiv.className = "message user-message";
        
        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";
        contentDiv.textContent = text;
        
        messageDiv.appendChild(contentDiv);
        chatFeed.appendChild(messageDiv);
        chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    // Create an empty assistant bubble that we will stream text into
    function createAssistantBubble() {
        const messageDiv = document.createElement("div");
        messageDiv.className = "message assistant-message";
        messageDiv.id = "streaming-assistant-bubble";
        
        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";
        contentDiv.innerHTML = `<span class="streaming-cursor"><i class="fa-solid fa-circle fa-beat-fade fa-xs icon-margin"></i></span>`;
        
        messageDiv.appendChild(contentDiv);
        chatFeed.appendChild(messageDiv);
        chatFeed.scrollTop = chatFeed.scrollHeight;
        
        return contentDiv;
    }

    // Reset Chat History
    btnReset.addEventListener("click", () => {
        chatHistory = [];
        chatFeed.innerHTML = `
            <div class="message assistant-message">
                <div class="message-content">
                    <p>Chào mừng bạn đến với <strong>DrugLaw RAG Dashboard</strong>! Tôi là trợ lý AI được tích hợp hệ thống RAG nâng cao để trả lời các câu hỏi về <strong>luật ma túy Việt Nam</strong> và <strong>tin tức tội phạm tệ nạn ma túy liên quan tới nghệ sĩ</strong>.</p>
                    <p>Lịch sử trò chuyện đã được xóa. Hãy nhập câu hỏi mới.</p>
                </div>
            </div>
        `;
        
        statusPanelGrid.style.display = "none";
        pipelineMeta.textContent = "Sẵn sàng";
        
        const emptyState = `<div class="empty-state">Nhập câu hỏi để bắt đầu...</div>`;
        listLexical.innerHTML = emptyState;
        listSemantic.innerHTML = emptyState;
        listReranked.innerHTML = emptyState;
        listSources.innerHTML = emptyState;
    });

    // Form Submit
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (query) {
            submitQuery(query);
        }
    });

    // =============================================================================
    // SUBMIT QUERY TO FASTAPI BACKEND (STREAMING READER)
    // =============================================================================
    async function submitQuery(query) {
        chatInput.value = "";
        appendUserMessage(query);
        
        // Setup empty assistant bubble for streaming
        const bubbleContentElement = createAssistantBubble();

        // Build Payload
        const payload = {
            query: query,
            history: chatHistory.slice(-10), // Limit to last 5 turns of conversation
            top_k: parseInt(paramTopK.value),
            score_threshold: parseFloat(paramThreshold.value),
            use_reranking: paramUseRerank.checked,
            rerank_method: paramRerankMethod.value,
            llm_model: paramLlmModel.value,
            temperature: parseFloat(paramTemp.value),
            system_prompt: promptSystemEditor ? promptSystemEditor.value : ""
        };

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Server returned status ${response.status}`);
            }

            // Read the ReadableStream
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let assistantText = "";
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                // Decode and append to buffer
                buffer += decoder.decode(value, { stream: true });
                
                // Split by newline to get individual lines
                const lines = buffer.split("\n");
                
                // Keep the last partial line in the buffer
                buffer = lines.pop();

                for (let line of lines) {
                    // Remove carriage return if present
                    if (line.endsWith("\r")) {
                        line = line.slice(0, -1);
                    }
                    
                    if (line.startsWith("data: ")) {
                        const dataContent = line.slice(6);
                        
                        if (dataContent.startsWith("__METADATA__:")) {
                            try {
                                const metadata = JSON.parse(dataContent.slice(13));
                                updateInspector(metadata);
                            } catch (parseErr) {
                                console.error("Failed to parse metadata JSON:", parseErr, "Data:", dataContent);
                            }
                        } else {
                            // Unescape newlines
                            const unescapedToken = dataContent.replace(/\\n/g, "\n");
                            assistantText += unescapedToken;
                            
                            // Update assistant text progressively
                            bubbleContentElement.innerHTML = formatMessageText(assistantText) + 
                                ` <span class="streaming-cursor"><i class="fa-solid fa-circle fa-beat-fade fa-xs" style="color:var(--accent-end);"></i></span>`;
                            chatFeed.scrollTop = chatFeed.scrollHeight;
                        }
                    }
                }
            }

            // Stream is fully done, clean up cursor and finalize citation bindings
            bubbleContentElement.innerHTML = formatMessageText(assistantText);
            
            // Save current interaction to history
            chatHistory.push({ role: "user", content: query });
            chatHistory.push({ role: "assistant", content: assistantText });
            
            // Remove temp streaming bubble ID
            const streamingBubble = document.getElementById("streaming-assistant-bubble");
            if (streamingBubble) streamingBubble.removeAttribute("id");

            // Bind click and hover events on the newly generated citation badges
            const badges = bubbleContentElement.querySelectorAll(".citation-badge");
            badges.forEach(badge => {
                badge.addEventListener("click", () => {
                    const targetText = badge.getAttribute("data-cite-target");
                    highlightSourceCard(targetText);
                });

                badge.addEventListener("mouseenter", (e) => {
                    const targetText = badge.getAttribute("data-cite-target");
                    const chunkText = getChunkTextByCitation(targetText);
                    if (chunkText) {
                        const previewText = chunkText.length > 220 ? chunkText.substring(0, 220) + "..." : chunkText;
                        citationTooltip.innerHTML = `<strong>Nguồn trích dẫn:</strong><br>${previewText}`;
                        citationTooltip.style.display = "block";
                        
                        // Position the tooltip
                        const rect = badge.getBoundingClientRect();
                        citationTooltip.style.left = `${rect.left + window.scrollX}px`;
                        citationTooltip.style.top = `${rect.bottom + window.scrollY + 6}px`;
                        
                        // Fade in
                        void citationTooltip.offsetWidth; // force reflow
                        citationTooltip.style.opacity = "1";
                        citationTooltip.style.transform = "translateY(0)";
                    }
                });

                badge.addEventListener("mouseleave", () => {
                    citationTooltip.style.opacity = "0";
                    citationTooltip.style.transform = "translateY(4px)";
                    setTimeout(() => {
                        if (citationTooltip.style.opacity === "0") {
                            citationTooltip.style.display = "none";
                        }
                    }, 150);
                });
            });

        } catch (error) {
            console.error("RAG Query Failed:", error);
            bubbleContentElement.innerHTML = `❌ <strong>Lỗi RAG Pipeline:</strong> Không thể nhận câu trả lời (${error.message}). Vui lòng kiểm tra cổng kết nối.`;
            const loadingBubble = document.getElementById("streaming-assistant-bubble");
            if (loadingBubble) loadingBubble.removeAttribute("id");
        }
    }

    // =============================================================================
    // INSPECTOR POPULATION
    // =============================================================================
    function updateInspector(data) {
        // Save current chunks globally for citation preview tooltip
        window.currentChunks = data.final_chunks || [];

        if (data.constructed_user_prompt && promptUserViewer) {
            promptUserViewer.textContent = data.constructed_user_prompt;
        }

        // Show status panel
        statusPanelGrid.style.display = "grid";
        statusLatency.textContent = `${data.latency_ms} ms`;
        
        if (data.fallback_active) {
            fallbackCard.className = "status-card glass fallback-warn";
            statusFallback.textContent = "PageIndex Fallback";
            pipelineMeta.textContent = `FALLBACK ACTIVE: ${data.fallback_reason}`;
        } else {
            fallbackCard.className = "status-card glass";
            statusFallback.textContent = "Không";
            pipelineMeta.textContent = "Truy xuất Hybrid tối ưu";
        }

        // 1. Populate Retrieval List (Lexical & Semantic)
        listLexical.innerHTML = "";
        if (!data.lexical || data.lexical.length === 0) {
            listLexical.innerHTML = `<div class="empty-state">Không tìm thấy kết quả từ khóa.</div>`;
        } else {
            data.lexical.forEach((r, idx) => {
                const source = r.metadata.source || "Nguồn tài liệu";
                const card = createInspectorCard(idx + 1, source, r.score.toFixed(2), r.content, "Score");
                card.addEventListener("click", () => openDocumentViewer(source, r.content));
                listLexical.appendChild(card);
            });
        }

        listSemantic.innerHTML = "";
        if (!data.semantic || data.semantic.length === 0) {
            listSemantic.innerHTML = `<div class="empty-state">Không tìm thấy kết quả ngữ nghĩa.</div>`;
        } else {
            data.semantic.forEach((r, idx) => {
                const source = r.metadata.source || "Nguồn tài liệu";
                const card = createInspectorCard(idx + 1, source, r.score.toFixed(3), r.content, "Cosine");
                card.addEventListener("click", () => openDocumentViewer(source, r.content));
                listSemantic.appendChild(card);
            });
        }

        // 2. Populate Reranked List
        listReranked.innerHTML = "";
        if (!data.reranked || data.reranked.length === 0) {
            listReranked.innerHTML = `<div class="empty-state">Không có kết quả Reranking.</div>`;
        } else {
            data.reranked.forEach((r, idx) => {
                const source = r.metadata.source || "Nguồn tài liệu";
                const retSrc = r.source || "hybrid";
                const badgeClass = retSrc === "hybrid" ? "badge-hybrid" : "badge-fallback";
                
                const card = createInspectorCard(idx + 1, source, r.score.toFixed(3), r.content, "Rerank Score");
                
                // Add Source badge
                const header = card.querySelector(".cohere-card-header span");
                const badgeSpan = document.createElement("span");
                badgeSpan.className = `badge ${badgeClass}`;
                badgeSpan.textContent = retSrc;
                header.appendChild(badgeSpan);
                
                card.addEventListener("click", () => openDocumentViewer(source, r.content));
                listReranked.appendChild(card);
            });
        }

        // 3. Populate Source Context (Final Chunks loaded into prompt)
        listSources.innerHTML = "";
        if (!data.final_chunks || data.final_chunks.length === 0) {
            listSources.innerHTML = `<div class="empty-state">Không có chunks được nạp vào Prompt.</div>`;
        } else {
            data.final_chunks.forEach((r, idx) => {
                const source = r.metadata.source || "Tài liệu";
                const docType = r.metadata.type || "unknown";
                
                const card = document.createElement("div");
                card.className = "cohere-card";
                card.id = `source-card-${idx}`;
                card.setAttribute("data-source-name", source);
                
                card.innerHTML = `
                    <div class="cohere-card-header">
                        <span>[Chunk ${idx}] Nguồn: <strong>${source}</strong> (Loại: ${docType})</span>
                        <span class="cohere-card-score">ID: ${idx} <i class="fa-solid fa-expand" style="margin-left:5px;"></i></span>
                    </div>
                    <div class="cohere-card-body">
                        <pre>${r.content}</pre>
                    </div>
                `;
                card.addEventListener("click", () => openDocumentViewer(source, r.content));
                listSources.appendChild(card);
            });
        }
    }

    function createInspectorCard(rank, source, score, content, label) {
        const card = document.createElement("div");
        card.className = "cohere-card";
        
        const preview = content.length > 130 ? content.substring(0, 130) + "..." : content;
        
        card.innerHTML = `
            <div class="cohere-card-header">
                <span>#${rank} - ${source}</span>
                <span class="cohere-card-score">${label}: ${score}</span>
            </div>
            <div class="cohere-card-body">${preview}</div>
        `;
        return card;
    }

    // =============================================================================
    // UX CITATION HIGHLIGHT AND SCROLL
    // =============================================================================
    function highlightSourceCard(targetText) {
        // Switch to Ground Truth Chunks Tab
        switchTab("tab-sources");
        
        // Find matching source card
        const cards = listSources.querySelectorAll(".cohere-card");
        let matchedCard = null;
        
        cards.forEach(card => {
            const cardSource = card.getAttribute("data-source-name").toLowerCase();
            const searchPattern = targetText.toLowerCase();
            
            if (cardSource.includes(searchPattern) || searchPattern.includes(cardSource)) {
                matchedCard = card;
            }
        });

        if (!matchedCard) {
            const indexMatch = targetText.match(/\d+/);
            if (indexMatch) {
                const idx = parseInt(indexMatch[0]);
                matchedCard = document.getElementById(`source-card-${idx}`);
            }
        }

        if (matchedCard) {
            matchedCard.scrollIntoView({ behavior: "smooth", block: "center" });
            
            matchedCard.classList.remove("highlight-source");
            void matchedCard.offsetWidth; // Trigger reflow to restart animation
            matchedCard.classList.add("highlight-source");
            
            setTimeout(() => {
                matchedCard.classList.remove("highlight-source");
            }, 2000);
        } else {
            console.log(`Could not find matching source card for citation: ${targetText}`);
        }
    }

    // =============================================================================
    // MODAL DOCUMENT VIEWER ACTIONS
    // =============================================================================
    modalClose.addEventListener("click", () => {
        docModal.style.display = "none";
    });

    docModal.addEventListener("click", (e) => {
        if (e.target === docModal) {
            docModal.style.display = "none";
        }
    });

    async function openDocumentViewer(filename, chunkContent) {
        if (!filename) return;
        
        modalTitle.textContent = "Đang tải tài liệu...";
        modalBodyMeta.textContent = `File: ${filename}`;
        modalBody.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin icon-margin"></i> Đang đọc dữ liệu từ máy chủ...</div>`;
        docModal.style.display = "flex";
        
        try {
            const res = await fetch(`/api/document?filename=${encodeURIComponent(filename)}`);
            if (!res.ok) {
                throw new Error("Không thể tải tệp tin");
            }
            const data = await res.json();
            
            let docContent = data.content;
            
            // Try to highlight the chunk inside the document content
            if (chunkContent) {
                const cleanChunk = chunkContent.trim();
                const idx = docContent.indexOf(cleanChunk);
                if (idx !== -1) {
                    docContent = docContent.substring(0, idx) + 
                                 `\n\n<div class="highlight-text-segment">\n\n${cleanChunk}\n\n</div>\n\n` + 
                                 docContent.substring(idx + cleanChunk.length);
                } else {
                    // Try matching the first 45 characters
                    const prefix = cleanChunk.substring(0, Math.min(cleanChunk.length, 45));
                    const pIdx = docContent.indexOf(prefix);
                    if (pIdx !== -1) {
                        const len = Math.min(cleanChunk.length, 120);
                        docContent = docContent.substring(0, pIdx) + 
                                     `\n\n<div class="highlight-text-segment">\n\n${docContent.substring(pIdx, pIdx + len)}...\n\n</div>\n\n` + 
                                     docContent.substring(pIdx + len);
                    }
                }
            }
            
            modalTitle.textContent = `Đọc tài liệu: ${filename}`;
            if (typeof marked !== 'undefined') {
                modalBody.innerHTML = marked.parse(docContent);
            } else {
                modalBody.innerHTML = `<pre>${docContent}</pre>`;
            }
            
            // Scroll to the highlighted element in the modal
            setTimeout(() => {
                const highlightEl = modalBody.querySelector(".highlight-text-segment");
                if (highlightEl) {
                    highlightEl.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            }, 150);
            
        } catch (err) {
            modalTitle.textContent = "Lỗi";
            modalBody.innerHTML = `<div class="empty-state" style="color: var(--accent-start); border-color: var(--accent-start);">
                <i class="fa-solid fa-triangle-exclamation icon-margin"></i> 
                Lỗi tải tài liệu: ${err.message}
            </div>`;
        }
    }

    function removeAccents(str) {
        return str.normalize("NFD")
                  .replace(/[\u0300-\u036f]/g, "")
                  .replace(/đ/g, "d")
                  .replace(/Đ/g, "D");
    }

    function findBestMatchingChunk(citeText) {
        if (!window.currentChunks || window.currentChunks.length === 0) return null;
        
        const rawClean = citeText.toLowerCase().trim();
        
        // 1. If it's a number within bounds
        const numMatch = rawClean.match(/\b\d+\b/);
        if (numMatch) {
            const val = parseInt(numMatch[0]);
            if (val >= 0 && val < window.currentChunks.length) {
                return window.currentChunks[val];
            }
            if (val - 1 >= 0 && val - 1 < window.currentChunks.length) {
                return window.currentChunks[val - 1];
            }
        }
        
        // 2. Accent-insensitive token-based matching
        const cleanCite = removeAccents(rawClean);
        const words = cleanCite.split(/[\s,.\-\/]+/)
                               .map(w => w.trim())
                               .filter(w => w.length > 2 && w !== "2023" && w !== "2024" && w !== "2025" && w !== "2026");
                               
        if (words.length === 0) {
            for (let chunk of window.currentChunks) {
                const src = removeAccents((chunk.metadata.source || "").toLowerCase());
                if (src.includes(cleanCite) || cleanCite.includes(src)) {
                    return chunk;
                }
            }
            return window.currentChunks[0];
        }
        
        // 3. Score chunks
        let bestChunk = null;
        let maxScore = -1;
        
        for (let chunk of window.currentChunks) {
            const src = removeAccents((chunk.metadata.source || "").toLowerCase());
            const url = removeAccents((chunk.metadata.url || "").toLowerCase());
            const content = removeAccents((chunk.content || "").toLowerCase());
            
            let score = 0;
            for (let word of words) {
                if (src.includes(word)) {
                    score += 10;
                }
                if (url.includes(word)) {
                    score += 8;
                }
                if (content.includes(word)) {
                    score += 1;
                }
            }
            
            if (score > maxScore && score > 0) {
                maxScore = score;
                bestChunk = chunk;
            }
        }
        
        if (bestChunk) {
            return bestChunk;
        }
        
        // 4. Try matching first word as fallback
        if (words.length > 0) {
            const firstWord = words[0];
            for (let chunk of window.currentChunks) {
                const src = removeAccents((chunk.metadata.source || "").toLowerCase());
                const url = removeAccents((chunk.metadata.url || "").toLowerCase());
                if (src.includes(firstWord) || url.includes(firstWord)) {
                    return chunk;
                }
            }
        }
        
        return window.currentChunks[0];
    }

    function getChunkTextByCitation(citeText) {
        const chunk = findBestMatchingChunk(citeText);
        return chunk ? chunk.content : null;
    }

    function getChunkMetadataByCitation(citeText) {
        const chunk = findBestMatchingChunk(citeText);
        return chunk ? chunk.metadata : null;
    }
});

