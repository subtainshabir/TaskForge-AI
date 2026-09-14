import { FolderKanban, Plus } from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import Button from "../../components/Button/Button.jsx";
import { EmptyState } from "../../components/StatePanel/StatePanel.jsx";
import "./Dashboard.css";

const SUMMARY = [
  { label: "Active projects", value: "0" },
  { label: "Open tasks", value: "0" },
  { label: "Completed this week", value: "0" },
];

function Dashboard() {
  return (
    <PageContainer
      title="Dashboard"
      subtitle="An overview of your workspace"
      actions={
        <Button variant="primary">
          <Plus size={16} aria-hidden="true" />
          New project
        </Button>
      }
    >
      <div className="dashboard__summary">
        {SUMMARY.map((item) => (
          <Card key={item.label}>
            <p className="dashboard__summary-label">{item.label}</p>
            <p className="dashboard__summary-value">{item.value}</p>
          </Card>
        ))}
      </div>

      <Card className="dashboard__empty-card">
        <EmptyState
          icon={<FolderKanban size={22} aria-hidden="true" />}
          title="No projects yet"
          description="Create your first project to start breaking work into tasks with TaskForge AI."
          action={
            <Button variant="primary">
              <Plus size={16} aria-hidden="true" />
              New project
            </Button>
          }
        />
      </Card>

      <div className="dashboard__badges">
        <Badge variant="ai">AI-suggested</Badge>
        <Badge variant="accent">In progress</Badge>
        <Badge variant="success">On track</Badge>
        <Badge variant="danger">Overdue</Badge>
      </div>
    </PageContainer>
  );
}

export default Dashboard;