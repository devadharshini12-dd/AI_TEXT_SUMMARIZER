import { useState } from "react";

function App() {
  const [text, setText] = useState("");
  const [summary, setSummary] = useState("");
  const [length, setLength] = useState("medium");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (!selectedFile) {
      return;
    }

    const allowedTypes = ["application/pdf", "text/plain"];

    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Please select a PDF or TXT file.");
      return;
    }

    setFile(selectedFile);
    setError("");
  };

  const handleSummarize = async () => {
    setError("");
    setSummary("");

    if (!text.trim() && !file) {
      setError("Please enter some text or upload a PDF/TXT file.");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();

      formData.append("text", text);
      formData.append("length", length);

      if (file) {
        formData.append("file", file);
      }

      const response = await fetch(
        "http://localhost:8000/api/summarize",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to generate the summary."
        );
      }

      setSummary(data.summary);
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect to the backend server."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setText("");
    setSummary("");
    setFile(null);
    setError("");
  };

  const handleCopy = async () => {
    if (!summary) {
      return;
    }

    await navigator.clipboard.writeText(summary);
  };

  const handleDownload = () => {
    if (!summary) {
      return;
    }

    const blob = new Blob([summary], {
      type: "text/plain",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "summary.txt";
    link.click();

    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">S</div>

          <div>
            <h1>SummarAI</h1>
            <p>AI Text Summarizer</p>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          AI Summarization
        </div>
      </header>

      <main className="main-container">
        <section className="hero">
          <p className="eyebrow">INTELLIGENT DOCUMENT ANALYSIS</p>

          <h2>
            Turn long content into
            <span> clear summaries.</span>
          </h2>

          <p className="hero-description">
            Paste an article or upload a document. SummarAI
            creates a concise and easy-to-understand summary
            based on your selected detail level.
          </p>
        </section>

        <section className="workspace">
          <div className="panel input-panel">
            <div className="panel-header">
              <div>
                <h3>Source content</h3>
                <p>Enter text or upload a document</p>
              </div>

              <button
                className="clear-button"
                onClick={handleClear}
              >
                Clear
              </button>
            </div>

            <textarea
              className="text-input"
              placeholder="Paste your article, notes, report, or any other text here..."
              value={text}
              onChange={(event) => setText(event.target.value)}
            />

            <div className="input-footer">
              <span>{text.length} characters</span>
            </div>

            <div className="divider">
              <span>OR</span>
            </div>

            <label className="upload-box">
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={handleFileChange}
              />

              <div className="upload-icon">+</div>

              <strong>
                {file ? file.name : "Upload a document"}
              </strong>

              <span>
                PDF or TXT files supported
              </span>
            </label>
          </div>

          <div className="panel settings-panel">
            <div className="panel-header">
              <div>
                <h3>Summary settings</h3>
                <p>Choose how detailed the result should be</p>
              </div>
            </div>

            <div className="length-options">
              <button
                className={
                  length === "short"
                    ? "length-card active"
                    : "length-card"
                }
                onClick={() => setLength("short")}
              >
                <strong>Short</strong>
                <span>
                  Very concise. Focuses only on the main idea.
                </span>
              </button>

              <button
                className={
                  length === "medium"
                    ? "length-card active"
                    : "length-card"
                }
                onClick={() => setLength("medium")}
              >
                <strong>Medium</strong>
                <span>
                  Balanced summary with the key supporting points.
                </span>
              </button>

              <button
                className={
                  length === "detailed"
                    ? "length-card active"
                    : "length-card"
                }
                onClick={() => setLength("detailed")}
              >
                <strong>Detailed</strong>
                <span>
                  Covers all major ideas and important details.
                </span>
              </button>
            </div>

            <button
              className="summarize-button"
              onClick={handleSummarize}
              disabled={loading}
            >
              {loading ? "Generating summary..." : "Generate Summary"}
            </button>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            <div className="info-box">
              <strong>How it works</strong>

              <p>
                Your content is processed by the AI backend
                and transformed into a readable summary without
                adding unrelated information.
              </p>
            </div>
          </div>
        </section>

        <section className="panel output-panel">
          <div className="panel-header">
            <div>
              <h3>Generated summary</h3>
              <p>Your AI-generated result will appear here</p>
            </div>

            {summary && (
              <div className="output-actions">
                <button onClick={handleCopy}>
                  Copy
                </button>

                <button onClick={handleDownload}>
                  Download
                </button>
              </div>
            )}
          </div>

          <div className="summary-area">
            {loading ? (
              <div className="loading-state">
                <div className="loading-line"></div>
                <div className="loading-line short"></div>
                <div className="loading-line"></div>
                <div className="loading-line medium"></div>
              </div>
            ) : summary ? (
              <p className="summary-text">{summary}</p>
            ) : (
              <div className="empty-state">
                <div className="empty-symbol">AI</div>

                <h4>Your summary will appear here</h4>

                <p>
                  Add some content and select a summary
                  length to get started.
                </p>
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="footer">
        <p>
          SummarAI · AI-powered text summarization
        </p>
      </footer>
    </div>
  );
}

export default App;