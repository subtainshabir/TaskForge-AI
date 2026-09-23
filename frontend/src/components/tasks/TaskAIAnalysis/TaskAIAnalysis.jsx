import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FolderCode,
  Gauge,
  Layers,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import Card from "../../Card/Card.jsx";
import Button from "../../Button/Button.jsx";
import Badge from "../../Badge/Badge.jsx";
import Spinner from "../../Spinner/Spinner.jsx";
import { taskService } from "../../../services/taskService.js";
import { apiErrorMessage } from "../../../utils/apiErrorMessage.js";
import "./TaskAIAnalysis.css";

const COMPLEXITY_META = {
  low: { label: "Low", badgeVariant: "neutral" },
  medium: { label: "Medium", badgeVariant: "accent" },
  high: { label: "High", badgeVariant: "danger" },
};

function TaskAIAnalysis({ taskId }) {
  const [analysis, setAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setError("");
    try {
      const data = await taskService.analyzeWithAI(taskId);
      setAnalysis(data);
    } catch (err) {
      setError(
        apiErrorMessage(
          err,
          "Failed to analyze task with AI. Please check your AI configuration and try again."
        )
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const complexityKey = (analysis?.complexity || "").toLowerCase();
  const complexityInfo = COMPLEXITY_META[complexityKey] || {
    label: analysis?.complexity || "Medium",
    badgeVariant: "accent",
  };

  return (
    <Card className={`task-ai-analysis ${analysis ? "task-ai-analysis--active" : ""}`}>
      <div className="task-ai-analysis__header">
        <h2 className="task-ai-analysis__title">
          <Sparkles size={18} className="task-ai-analysis__sparkle-icon" aria-hidden="true" />
          AI Task Understanding
        </h2>
        <Button
          variant={analysis ? "secondary" : "primary"}
          size="sm"
          disabled={isAnalyzing}
          onClick={handleAnalyze}
          aria-label={analysis ? "Re-analyze task with AI" : "Analyze task with AI"}
        >
          {isAnalyzing ? (
            <>
              <Spinner size="sm" label="Analyzing" />
              Analyzing task...
            </>
          ) : analysis ? (
            <>
              <RefreshCw size={14} aria-hidden="true" />
              Re-analyze
            </>
          ) : (
            <>
              <Sparkles size={14} aria-hidden="true" />
              Analyze with AI
            </>
          )}
        </Button>
      </div>

      {error && (
        <div className="task-ai-analysis__error" role="alert">
          <span>{error}</span>
          <Button variant="secondary" size="sm" onClick={handleAnalyze}>
            Try again
          </Button>
        </div>
      )}

      {isAnalyzing && (
        <div className="task-ai-analysis__loading-state" aria-live="polite">
          <Spinner size="lg" label="Analyzing task requirements" />
          <p className="task-ai-analysis__loading-text">
            Analyzing task goals, complexity, and technical requirements...
          </p>
        </div>
      )}

      {!isAnalyzing && !analysis && (
        <div className="task-ai-analysis__empty-state">
          <p className="task-ai-analysis__empty-text">
            Extract structured insights for this task, including primary goals, estimated
            complexity, required skills, and potential implementation obstacles.
          </p>
          <Button variant="secondary" onClick={handleAnalyze}>
            <Sparkles size={14} aria-hidden="true" />
            Analyze with AI
          </Button>
        </div>
      )}

      {!isAnalyzing && analysis && (
        <div className="task-ai-analysis__content">
          <div className="task-ai-analysis__block task-ai-analysis__block--full">
            <h3 className="task-ai-analysis__label">Summary</h3>
            <p className="task-ai-analysis__value">{analysis.summary}</p>
          </div>

          <div className="task-ai-analysis__block task-ai-analysis__block--full">
            <h3 className="task-ai-analysis__label">Goal</h3>
            <p className="task-ai-analysis__value">{analysis.goal}</p>
          </div>

          <div className="task-ai-analysis__grid">
            <div className="task-ai-analysis__block">
              <h3 className="task-ai-analysis__label">Category</h3>
              <div>
                <Badge variant="neutral">
                  <FolderCode size={12} aria-hidden="true" />
                  {analysis.category}
                </Badge>
              </div>
            </div>

            <div className="task-ai-analysis__block">
              <h3 className="task-ai-analysis__label">Complexity</h3>
              <div>
                <Badge variant={complexityInfo.badgeVariant}>
                  <Gauge size={12} aria-hidden="true" />
                  {complexityInfo.label}
                </Badge>
              </div>
            </div>
          </div>

          {analysis.skills && analysis.skills.length > 0 && (
            <div className="task-ai-analysis__block task-ai-analysis__block--full">
              <h3 className="task-ai-analysis__label">Required Skills</h3>
              <div className="task-ai-analysis__tags">
                {analysis.skills.map((skill, index) => (
                  <span key={index} className="task-ai-analysis__skill-tag">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.potential_challenges && analysis.potential_challenges.length > 0 && (
            <div className="task-ai-analysis__block task-ai-analysis__block--full">
              <h3 className="task-ai-analysis__label">Potential Challenges</h3>
              <ul className="task-ai-analysis__challenges">
                {analysis.potential_challenges.map((challenge, index) => (
                  <li key={index} className="task-ai-analysis__challenge-item">
                    <AlertTriangle size={14} className="task-ai-analysis__challenge-bullet" aria-hidden="true" />
                    <span>{challenge}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default TaskAIAnalysis;
