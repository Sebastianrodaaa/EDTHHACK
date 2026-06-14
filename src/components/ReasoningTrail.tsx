import React, { useState } from "react";
import {
  LayoutAnimation,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  UIManager,
  View,
} from "react-native";
import {
  CheckCircle2,
  Circle,
  CircleAlert,
  CircleDotDashed,
  CircleX,
} from "lucide-react-native";
import { colors, radius, space, type } from "../theme";
import { GlassCard } from "./GlassCard";
import { useAppStore, type Status, type Subtask, type Task } from "../store";

if (
  Platform.OS === "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const STATUS_COLOR: Record<Status, string> = {
  completed: colors.green,
  "in-progress": colors.blue,
  "need-help": colors.orange,
  failed: colors.red,
  pending: colors.tertiary,
};

const STATUS_LABEL: Record<Status, string> = {
  completed: "Completed",
  "in-progress": "In Progress",
  "need-help": "Needs Help",
  failed: "Failed",
  pending: "Pending",
};

function withAlpha(c: string, a: number) {
  // expand #RRGGBB to rgba; pass-through for non-hex
  if (c[0] !== "#" || c.length < 7) return c;
  const r = parseInt(c.slice(1, 3), 16);
  const g = parseInt(c.slice(3, 5), 16);
  const b = parseInt(c.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function StatusIcon({ status, size }: { status: Status; size: number }) {
  const props = { size, color: STATUS_COLOR[status], strokeWidth: 2 } as const;
  switch (status) {
    case "completed":
      return <CheckCircle2 {...props} />;
    case "in-progress":
      return <CircleDotDashed {...props} />;
    case "need-help":
      return <CircleAlert {...props} />;
    case "failed":
      return <CircleX {...props} />;
    default:
      return <Circle {...props} />;
  }
}

function easeNext() {
  LayoutAnimation.configureNext(
    LayoutAnimation.create(240, "easeInEaseOut", "opacity")
  );
}

export function ReasoningTrail() {
  const tasks = useAppStore((s) => s.tasks);
  const [expandedTasks, setExpandedTasks] = useState<string[]>(["1", "2", "3", "4"]);
  const [expandedSubs, setExpandedSubs] = useState<Record<string, boolean>>({});

  const toggleTask = (id: string) => {
    easeNext();
    setExpandedTasks((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };
  const toggleSub = (taskId: string, subId: string) => {
    easeNext();
    const key = `${taskId}-${subId}`;
    setExpandedSubs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <GlassCard style={styles.panel}>
      <View style={styles.header}>
        <Text style={styles.title}>Reasoning trail</Text>
        <Text style={styles.count}>{tasks.length} stages</Text>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {tasks.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            expanded={expandedTasks.includes(task.id)}
            expandedSubs={expandedSubs}
            onToggleTask={() => toggleTask(task.id)}
            onToggleSub={toggleSub}
          />
        ))}
      </ScrollView>
    </GlassCard>
  );
}

function TaskRow({
  task,
  expanded,
  expandedSubs,
  onToggleTask,
  onToggleSub,
}: {
  task: Task;
  expanded: boolean;
  expandedSubs: Record<string, boolean>;
  onToggleTask: () => void;
  onToggleSub: (taskId: string, subId: string) => void;
}) {
  const done = task.status === "completed";
  return (
    <View style={styles.taskBlock}>
      <Pressable
        style={({ pressed }) => [styles.taskRow, pressed && styles.pressed]}
        onPress={onToggleTask}
      >
        <View style={styles.iconSlot}>
          <StatusIcon status={task.status} size={20} />
        </View>
        <Text style={[styles.taskTitle, done && styles.dim]} numberOfLines={1}>
          {task.title}
        </Text>
        <View style={styles.rowRight}>
          {task.dependencies.map((dep) => (
            <View key={dep} style={styles.depChip}>
              <Text style={styles.depText}>{dep}</Text>
            </View>
          ))}
          <StatusBadge status={task.status} />
        </View>
      </Pressable>

      {expanded && task.subtasks.length > 0 ? (
        <View style={styles.subWrap}>
          <View style={styles.connector} />
          {task.subtasks.map((sub) => (
            <SubtaskRow
              key={sub.id}
              sub={sub}
              expanded={!!expandedSubs[`${task.id}-${sub.id}`]}
              onToggle={() => onToggleSub(task.id, sub.id)}
            />
          ))}
        </View>
      ) : null}
    </View>
  );
}

function SubtaskRow({
  sub,
  expanded,
  onToggle,
}: {
  sub: Subtask;
  expanded: boolean;
  onToggle: () => void;
}) {
  const done = sub.status === "completed";
  return (
    <View>
      <Pressable
        style={({ pressed }) => [styles.subRow, pressed && styles.pressed]}
        onPress={onToggle}
      >
        <View style={styles.subIconSlot}>
          <StatusIcon status={sub.status} size={16} />
        </View>
        <Text style={[styles.subTitle, done && styles.dim]} numberOfLines={1}>
          {sub.title}
        </Text>
      </Pressable>

      {expanded ? (
        <View style={styles.subDetail}>
          <Text style={styles.subDesc}>{sub.description}</Text>
          {sub.tools && sub.tools.length > 0 ? (
            <View style={styles.toolsRow}>
              <Text style={styles.toolsLabel}>MCP Servers</Text>
              <View style={styles.toolsWrap}>
                {sub.tools.map((tool) => (
                  <View key={tool} style={styles.toolChip}>
                    <Text style={styles.toolText}>{tool}</Text>
                  </View>
                ))}
              </View>
            </View>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function StatusBadge({ status }: { status: Status }) {
  const color = STATUS_COLOR[status];
  return (
    <View style={[styles.badge, { backgroundColor: withAlpha(color, 0.16) }]}>
      <Text style={[styles.badgeText, { color }]}>{STATUS_LABEL[status]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    paddingBottom: space.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.hairline,
  },
  title: { ...type.headline, color: colors.label },
  count: { ...type.footnote, color: colors.secondary },

  scroll: { flex: 1 },
  scrollContent: { paddingVertical: space.sm, paddingHorizontal: space.sm },

  taskBlock: { marginBottom: 2 },
  taskRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: space.sm,
    paddingVertical: 9,
    borderRadius: radius.control,
    gap: space.sm,
  },
  pressed: { backgroundColor: colors.fill },
  iconSlot: { width: 24, alignItems: "center" },
  taskTitle: { ...type.callout, fontWeight: "600", color: colors.label, flex: 1 },
  dim: { color: colors.tertiary },
  rowRight: { flexDirection: "row", alignItems: "center", gap: 6 },

  depChip: {
    backgroundColor: colors.fill,
    borderRadius: radius.chip,
    minWidth: 20,
    paddingHorizontal: 6,
    paddingVertical: 2,
    alignItems: "center",
  },
  depText: { ...type.caption2, color: colors.secondary },

  badge: { borderRadius: radius.pill, paddingHorizontal: 9, paddingVertical: 3 },
  badgeText: { ...type.caption2, fontWeight: "600" },

  subWrap: { marginLeft: 20, paddingLeft: 16, position: "relative" },
  connector: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 12,
    width: StyleSheet.hairlineWidth,
    backgroundColor: colors.hairlineStrong,
  },
  subRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 5,
    paddingHorizontal: space.sm,
    borderRadius: radius.control,
    gap: space.sm,
  },
  subIconSlot: { width: 20, alignItems: "center" },
  subTitle: { ...type.subhead, color: colors.secondary, flex: 1 },

  subDetail: { marginLeft: 28, paddingRight: space.sm, paddingVertical: 4, gap: 8 },
  subDesc: { ...type.footnote, color: colors.tertiary, lineHeight: 18 },
  toolsRow: { gap: 6 },
  toolsLabel: { ...type.caption2, color: colors.secondary, fontWeight: "600" },
  toolsWrap: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  toolChip: {
    backgroundColor: colors.fill,
    borderRadius: radius.chip,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  toolText: { ...type.caption, color: colors.secondary },
});
