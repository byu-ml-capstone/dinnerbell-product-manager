import { useDroppable } from "@dnd-kit/core";
import { StoryCard } from "./StoryCard";

export function BoardColumn({ id, label, stories, memberName, onStatus, onOpen, readOnly }) {
  const { setNodeRef, isOver } = useDroppable({ id, disabled: readOnly });
  return (
    <section ref={setNodeRef} className={isOver ? "column over" : "column"}>
      <header>
        <h3>{label}</h3>
        <span>{stories.length}</span>
      </header>
      <div className="cards">
        {stories.map((story) => (
          <StoryCard
            key={story.id}
            story={story}
            memberName={memberName(story.assignee_id)}
            onStatus={onStatus}
            onOpen={onOpen}
            readOnly={readOnly}
          />
        ))}
      </div>
    </section>
  );
}
