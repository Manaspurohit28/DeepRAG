let globalContext = "";
let qaMode = "auto";
let generatedResults = [];
const spinner = document.getElementById("spinner-overlay");
const autoControls = document.getElementById("auto-controls");

document.getElementById("qa-mode").addEventListener("change", function () {
  qaMode = this.value;
  autoControls.style.display = qaMode === "auto" ? "block" : "none";
});


document.getElementById("upload-btn").addEventListener("click", async () => {
  const file = document.getElementById("pdf-upload").files[0];
  if (!file) return alert("Please select a PDF.");

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/upload", { method: "POST", body: formData });
  const data = await res.json();

  if (data.context) {
    globalContext = data.context;
    alert("PDF uploaded and context extracted.");
  }
});

document.getElementById("generate-btn").addEventListener("click", async () => {
  if (!globalContext) return alert("Please upload a PDF first.");
  const count = document.getElementById("qa-count").value;

  showSpinner();
  const res = await fetch("/generate_qa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context: globalContext, count: parseInt(count) }),
  });

  const data = await res.json();
  const qaPairs = data.qa_pairs;
  displayQAPairs(qaPairs);

  const evalRes = await fetch("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context: globalContext, qa_pairs: qaPairs }),
  });

  const evalData = await evalRes.json();
  displayEvaluationTable(evalData.results);
  generatedResults = evalData.results;
  hideSpinner();
});

function displayQAPairs(pairs) {
  const qaDiv = document.getElementById("qa-results");
  qaDiv.innerHTML = "<h4>Generated QA Pairs:</h4>";
  pairs.forEach(([q, a], i) => {
    const block = document.createElement("div");
    block.className = "qa-block";
    block.innerHTML = `<strong>Q${i + 1}:</strong> ${q}<br/><strong>A:</strong> ${a}`;
    qaDiv.appendChild(block);
  });
}

function displayEvaluationTable(results) {
  const qaDiv = document.getElementById("qa-results");
  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr><th>Question</th><th>Actual Answer</th><th>RAG Answer</th><th>Score</th><th>Pass/Fail</th></tr>
    </thead>
    <tbody>
      ${results.map(r => `
        <tr>
          <td>${r.question}</td>
          <td>${r.llm_answer}</td>
          <td>${r.rag_answer}</td>
          <td>${r.score}</td>
          <td class="${r.pass === "Pass" ? "pass" : "fail"}">${r.pass}</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  qaDiv.appendChild(table);
}

async function sendMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  appendChat("user", message);
  input.value = "";
  showTyping();

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, context: globalContext }),
  });

  const data = await res.json();
  const { response, rag_answer, llm_answer } = data;
  appendChat("assistant", response);
  hideTyping();

  if (qaMode === "manual") {
    document.getElementById("eval-status").innerText = "Evaluation in progress...";
    showSpinner();
  
    const evalRes = await fetch("/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        context: globalContext,
        qa_pairs: [[message, llm_answer]]  // compare base LLM vs RAG
      })
    });
  
    const evalData = await evalRes.json();
    hideSpinner();
  
    const result = evalData.results[0];
    document.getElementById("eval-status").innerText = `Evaluation: Score ${result.score} - ${result.pass}`;
    displayEvaluationTable([result]);
  }
  
}

function appendChat(role, text) {
  const chatBox = document.getElementById("chat-box");
  const msg = document.createElement("div");
  msg.className = role === "user" ? "chat-message user" : "chat-message assistant";
  msg.innerText = text;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping() {
  const chatBox = document.getElementById("chat-box");
  const typing = document.createElement("div");
  typing.className = "typing";
  typing.innerText = "Assistant is typing...";
  typing.id = "typing";
  chatBox.appendChild(typing);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
  const typing = document.getElementById("typing");
  if (typing) typing.remove();
}

function showSpinner() {
  spinner.style.display = "flex";
}

function hideSpinner() {
  spinner.style.display = "none";
}

document.getElementById("download-btn").addEventListener("click", () => {
  if (generatedResults.length === 0) return alert("No results to download.");
  const rows = [["Question", "Actual Answer", "RAG Answer", "Score", "Pass/Fail"]];
  generatedResults.forEach(r => {
    rows.push([r.question, r.llm_answer, r.rag_answer, r.score, r.pass]);
  });

  const csv = rows.map(row => row.map(v => `"${v}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "evaluation_results.csv";
  a.click();
});
