import TaskItem from "../TaskItem/TaskItem.jsx";
import "./TaskList.css";

function TaskList({
  tasks,
  isLoading,
  projectId,
  onStatusChange,
  onPriorityChange,
  onToggleComplete,
  onEdit,
  onDelete,
}) {
  if (isLoading) {
    return (
      <div className="task-list" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="task-item-skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="task-list">
      {tasks.map((task) => (
        <TaskItem
          key={task.id}
          task={task}
          projectId={projectId}
          onStatusChange={onStatusChange}
          onPriorityChange={onPriorityChange}
          onToggleComplete={onToggleComplete}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}

export default TaskList;