import "./TaskDescription.css";

function TaskDescription({ description }) {
  if (!description) {
    return <p className="task-description task-description--empty">No description provided.</p>;
  }
  return <p className="task-description">{description}</p>;
}

export default TaskDescription;