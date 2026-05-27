import { useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

type Direction = "zh_to_en" | "en_to_zh";

type ReplacementOption = {
  translatedMention: string;
  replacement: string;
  zh: string;
  en: string;
};

type ChatMessage = {
  speaker: string;
  original: string;
  translation: string;
  notes: string[];
  copyText: string;
  replacementOptions?: ReplacementOption[];
};

type TranslationInputType = "text" | "screenshot";

type TranslationResponse = {
  inputType: TranslationInputType;
  messages?: ChatMessage[];
};

const findFirstCaseInsensitiveSpan = (text: string, needle: string) => {
  if (!needle.trim()) return null;

  const index = text.toLowerCase().indexOf(needle.toLowerCase());
  if (index === -1) return null;

  return {
    start: index,
    end: index + needle.length,
  };
};

const spansOverlap = (
  first: { start: number; end: number },
  second: { start: number; end: number },
) => first.start < second.end && second.start < first.end;

const applyReplacementOptions = (
  originalText: string,
  options: ReplacementOption[],
) => {
  const replacements = options
    .map((option) => {
      const span = findFirstCaseInsensitiveSpan(
        originalText,
        option.translatedMention,
      );

      if (!span) return null;

      return {
        ...span,
        replacement: option.replacement,
      };
    })
    .filter((replacement): replacement is NonNullable<typeof replacement> =>
      Boolean(replacement),
    )
    .sort((first, second) => {
      const lengthDiff =
        second.end - second.start - (first.end - first.start);

      return lengthDiff || first.start - second.start;
    });

  const accepted: typeof replacements = [];

  for (const replacement of replacements) {
    if (!accepted.some((acceptedReplacement) =>
      spansOverlap(replacement, acceptedReplacement),
    )) {
      accepted.push(replacement);
    }
  }

  accepted.sort((first, second) => first.start - second.start);

  let output = "";
  let cursor = 0;

  for (const replacement of accepted) {
    output += originalText.slice(cursor, replacement.start);
    output += replacement.replacement;
    cursor = replacement.end;
  }

  return output + originalText.slice(cursor);
};

function App() {
  const isComposingRef = useRef(false);
  const requestControllerRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [text, setText] = useState("");
  const [direction, setDirection] = useState<Direction>("zh_to_en");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputType, setInputType] = useState<TranslationInputType>("text");
  const [outputText, setOutputText] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedOptions, setSelectedOptions] = useState<
    Record<string, ReplacementOption>
  >({});
  const [loading, setLoading] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">(
    "idle",
  );

  const toggleDirection = () => {
    setDirection((prev) => (prev === "zh_to_en" ? "en_to_zh" : "zh_to_en"));
  };

  const clearPage = () => {
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    setText("");
    setMessages([]);
    setInputType("text");
    setOutputText("");
    setErrorMessage("");
    setSelectedOptions({});
    setLoading(false);
    setNotesOpen(false);
    setCopyStatus("idle");
  };

  const applyResponse = (data: TranslationResponse) => {
    const nextMessages = data.messages ?? [];
    const firstMessage = nextMessages[0] ?? null;

    setInputType(data.inputType);
    setMessages(nextMessages);
    setOutputText(firstMessage?.copyText ?? "");
  };

  const translateText = async (inputText = text) => {
    const textToTranslate = inputText.trim();

    if (!textToTranslate) return;

    requestControllerRef.current?.abort();
    const controller = new AbortController();
    requestControllerRef.current = controller;
    const timeoutId = window.setTimeout(() => controller.abort(), 30000);

    setLoading(true);
    setMessages([]);
    setInputType("text");
    setOutputText("");
    setErrorMessage("");
    setSelectedOptions({});
    setNotesOpen(false);
    setCopyStatus("idle");

    try {
      const response = await fetch(`${API_BASE_URL}/translate-text`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        signal: controller.signal,
        body: JSON.stringify({
          text: textToTranslate,
          direction,
        }),
      });

      if (!response.ok) {
        throw new Error("Translation failed");
      }

      applyResponse(await response.json());
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error instanceof DOMException && error.name === "AbortError"
          ? "Translate timed out. Press Enter to try again."
          : "Translate failed. Check backend.",
      );
    } finally {
      window.clearTimeout(timeoutId);

      if (requestControllerRef.current === controller) {
        requestControllerRef.current = null;
        setLoading(false);
      }
    }
  };

  const translateScreenshot = async (file: File) => {
    requestControllerRef.current?.abort();
    const controller = new AbortController();
    requestControllerRef.current = controller;
    const timeoutId = window.setTimeout(() => controller.abort(), 30000);
    const formData = new FormData();

    formData.append("image", file);
    formData.append("direction", direction);

    setLoading(true);
    setMessages([]);
    setInputType("screenshot");
    setOutputText("");
    setErrorMessage("");
    setSelectedOptions({});
    setNotesOpen(false);
    setCopyStatus("idle");

    try {
      const response = await fetch(`${API_BASE_URL}/translate-screenshot`, {
        method: "POST",
        signal: controller.signal,
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Screenshot translation failed");
      }

      applyResponse(await response.json());
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error instanceof DOMException && error.name === "AbortError"
          ? "Image translation timed out. Try again."
          : "Image translation failed. Check backend.",
      );
    } finally {
      window.clearTimeout(timeoutId);

      if (requestControllerRef.current === controller) {
        requestControllerRef.current = null;
        setLoading(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (isComposingRef.current || e.nativeEvent.isComposing) {
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      translateText(e.currentTarget.value);
    }
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];

    if (!file) return;

    translateScreenshot(file);
    e.target.value = "";
  };

  const copyResult = async () => {
    if (!outputText) return;

    const fallbackCopy = () => {
      const textArea = document.createElement("textarea");
      textArea.value = outputText;
      textArea.style.position = "fixed";
      textArea.style.left = "-9999px";
      textArea.style.top = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const copied = document.execCommand("copy");
      document.body.removeChild(textArea);

      if (!copied) {
        throw new Error("Fallback copy failed");
      }
    };

    try {
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(outputText);
        } catch {
          fallbackCopy();
        }
      } else {
        fallbackCopy();
      }

      setCopyStatus("copied");
      window.setTimeout(() => setCopyStatus("idle"), 1600);
    } catch (error) {
      console.error(error);
      setCopyStatus("failed");
      window.setTimeout(() => setCopyStatus("idle"), 2200);
    }
  };

  const chooseReplacement = (option: ReplacementOption) => {
    const firstMessage = messages[0];

    if (!firstMessage) return;

    const nextSelectedOptions = {
      ...selectedOptions,
      [option.translatedMention]: option,
    };

    setSelectedOptions(nextSelectedOptions);
    setOutputText(
      applyReplacementOptions(
        firstMessage.copyText,
        Object.values(nextSelectedOptions),
      ),
    );
    setCopyStatus("idle");
  };

  const firstMessage = messages[0];
  const result = firstMessage;
  const isScreenshotResult = inputType === "screenshot";
  const replacementGroups = firstMessage?.replacementOptions?.reduce<
    Record<string, ReplacementOption[]>
  >((groups, option) => {
    groups[option.translatedMention] ??= [];
    groups[option.translatedMention].push(option);
    return groups;
  }, {});

  return (
    <div className="app-root">
      <div className="translator-box">
        <div className="input-controls">
          <button
            aria-label="Switch translation direction"
            className="lang-btn"
            onClick={toggleDirection}
            type="button"
          >
            {direction === "zh_to_en" ? "EN" : "中"}
          </button>
          <input
            accept="image/png,image/jpeg,image/jpg,image/webp"
            className="image-input"
            onChange={handleImageChange}
            ref={fileInputRef}
            type="file"
          />
          <button
            aria-label="Upload screenshot"
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            +
          </button>
        </div>

        <textarea
          className="translator-input"
          placeholder="Type ESO chat..."
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setErrorMessage("");
          }}
          onCompositionEnd={() => {
            isComposingRef.current = false;
          }}
          onCompositionStart={() => {
            isComposingRef.current = true;
          }}
          onKeyDown={handleKeyDown}
        />

        {loading && <div className="status-text">Translating...</div>}
        {errorMessage && <div className="error-text">{errorMessage}</div>}

        {result && (
          <div className="result-box">
            <button
              aria-label="Clear result"
              className="close-result-btn"
              onClick={clearPage}
              type="button"
            >
              X
            </button>
            {isScreenshotResult ? (
              <div className="message-list">
                {messages.map((message, index) => (
                  <div className="message-result" key={`${message.original}-${index}`}>
                    {message.original && (
                      <div className="message-original">{message.original}</div>
                    )}
                    <div className="result-text">{message.copyText}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="result-text">{outputText}</div>
            )}

            {result.notes.length > 0 && (
              <>
                <button
                  className="notes-toggle"
                  onClick={() => setNotesOpen((prev) => !prev)}
                  type="button"
                >
                  <span>{notesOpen ? "▲" : "▼"}</span>
                  <span>Notes</span>
                </button>

                {notesOpen && (
                  <div className="notes-box">
                    {result.notes.map((note) => (
                      <div className="note-text" key={note}>
                        {note}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {replacementGroups && Object.keys(replacementGroups).length > 0 && (
              <div className="replacement-panel">
                {Object.entries(replacementGroups).map(([mention, options]) => (
                  <div className="replacement-group" key={mention}>
                    <div className="replacement-label">{mention}</div>
                    <div className="replacement-options">
                      {options.map((option) => {
                        const isSelected =
                          selectedOptions[mention]?.replacement ===
                          option.replacement;

                        return (
                          <button
                            className={`replacement-option${
                              isSelected ? " selected" : ""
                            }`}
                            key={`${mention}-${option.zh}-${option.en}`}
                            onClick={() => chooseReplacement(option)}
                            type="button"
                          >
                            <span>{option.zh}</span>
                            <span>{option.en}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!isScreenshotResult && (
              <button
                className="copy-btn"
                disabled={!outputText}
                onClick={copyResult}
                type="button"
              >
                {copyStatus === "copied"
                  ? "Copied"
                  : copyStatus === "failed"
                    ? "Copy failed"
                    : "Copy"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
