import { TaskView } from "@/components/TaskView";

export default function TaskPage({ params }: { params: { id: string } }) {
  return <TaskView taskId={params.id} />;
}

