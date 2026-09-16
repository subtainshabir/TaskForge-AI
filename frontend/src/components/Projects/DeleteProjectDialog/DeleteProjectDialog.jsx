import Modal from "../../Modal/Modal.jsx";
import Button from "../../Button/Button.jsx";

function DeleteProjectDialog({ project, open, isDeleting, apiError, onConfirm, onCancel }) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title="Delete project?"
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button type="button" variant="danger" loading={isDeleting} onClick={onConfirm}>
            Delete project
          </Button>
        </>
      }
    >
      <p>
        Are you sure you want to delete <strong>{project?.name}</strong>? This action cannot be
        undone.
      </p>
      {apiError && (
        <p role="alert" style={{ color: "var(--color-danger)", marginTop: "var(--space-3)" }}>
          {apiError}
        </p>
      )}
    </Modal>
  );
}

export default DeleteProjectDialog;