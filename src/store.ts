import { create } from "zustand";

export type OrbMode = "white" | "red";
export type Status =
  | "completed"
  | "in-progress"
  | "pending"
  | "need-help"
  | "failed";

export interface Subtask {
  id: string;
  title: string;
  description: string;
  status: Status;
  tools?: string[];
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: Status;
  level: number;
  dependencies: string[];
  subtasks: Subtask[];
}

interface AppState {
  mode: OrbMode;
  tasks: Task[];
  trigger: () => void;
  standDown: () => void;
  toggle: () => void;
}

// Fixed reasoning structure for the acoustic counter-drone agent.
function buildTasks(): Task[] {
  return [
    {
      id: "1",
      title: "Acoustic Signal Acquisition",
      description: "Ingest and condition the body-worn mic-array stream.",
      status: "in-progress",
      level: 0,
      dependencies: [],
      subtasks: [
        {
          id: "1.1",
          title: "Capture audio frame",
          description: "Buffer 50 ms frames from the mic array.",
          status: "in-progress",
          tools: ["mic-array", "audio-buffer"],
        },
        {
          id: "1.2",
          title: "Compute RMS & SNR",
          description: "Measure level against the ambient noise floor.",
          status: "pending",
          tools: ["dsp-engine"],
        },
        {
          id: "1.3",
          title: "Detect energy spike",
          description: "Flag frames crossing the adaptive threshold.",
          status: "pending",
          tools: ["vad", "dsp-engine"],
        },
      ],
    },
    {
      id: "2",
      title: "Spectral Analysis",
      description: "Extract frequency-domain features from the frame.",
      status: "pending",
      level: 0,
      dependencies: [],
      subtasks: [
        {
          id: "2.1",
          title: "FFT / spectrogram",
          description: "Transform the frame into the frequency domain.",
          status: "pending",
          tools: ["dsp-engine"],
        },
        {
          id: "2.2",
          title: "Dominant frequency",
          description: "Locate the fundamental rotor / prop tone.",
          status: "pending",
          tools: ["peak-finder"],
        },
        {
          id: "2.3",
          title: "Harmonic comb check",
          description: "Detect evenly spaced harmonics of the fundamental.",
          status: "pending",
          tools: ["harmonic-analyzer"],
        },
      ],
    },
    {
      id: "3",
      title: "Classification",
      description: "Decide whether the signature is drone-like.",
      status: "pending",
      level: 1,
      dependencies: ["1", "2"],
      subtasks: [
        {
          id: "3.1",
          title: "Match signature library",
          description: "Compare features against known UAS profiles.",
          status: "pending",
          tools: ["signature-db"],
        },
        {
          id: "3.2",
          title: "Score drone-likeness",
          description: "Run the acoustic classifier model.",
          status: "pending",
          tools: ["classifier-model"],
        },
        {
          id: "3.3",
          title: "Calibrate confidence",
          description: "Temperature-scale the raw classifier score.",
          status: "pending",
          tools: ["calibrator"],
        },
      ],
    },
    {
      id: "4",
      title: "Threat Assessment",
      description: "Localize the source and recommend operator action.",
      status: "pending",
      level: 1,
      dependencies: ["3"],
      subtasks: [
        {
          id: "4.1",
          title: "Estimate bearing",
          description: "Direction-of-arrival from inter-mic phase delay.",
          status: "pending",
          tools: ["doa-estimator"],
        },
        {
          id: "4.2",
          title: "Assess threat level",
          description: "Fuse confidence, SNR and approach trend.",
          status: "pending",
          tools: ["fusion-engine"],
        },
        {
          id: "4.3",
          title: "Recommend action",
          description: "Advise visual confirm and cue effector.",
          status: "pending",
          tools: ["c2-advisor"],
        },
      ],
    },
  ];
}

type StatusUpdate = { delay: number; task: string; sub?: string; status: Status };

// Progressive reasoning cascade played out when a detection fires.
const DETECTION_CASCADE: StatusUpdate[] = [
  { delay: 0, task: "1", sub: "1.1", status: "completed" },
  { delay: 0, task: "1", sub: "1.2", status: "in-progress" },
  { delay: 550, task: "1", sub: "1.2", status: "completed" },
  { delay: 550, task: "1", sub: "1.3", status: "in-progress" },
  { delay: 1050, task: "1", sub: "1.3", status: "completed" },
  { delay: 1050, task: "1", status: "completed" },
  { delay: 1050, task: "2", status: "in-progress" },
  { delay: 1050, task: "2", sub: "2.1", status: "in-progress" },
  { delay: 1550, task: "2", sub: "2.1", status: "completed" },
  { delay: 1550, task: "2", sub: "2.2", status: "in-progress" },
  { delay: 2050, task: "2", sub: "2.2", status: "completed" },
  { delay: 2050, task: "2", sub: "2.3", status: "in-progress" },
  { delay: 2550, task: "2", sub: "2.3", status: "completed" },
  { delay: 2550, task: "2", status: "completed" },
  { delay: 2550, task: "3", status: "in-progress" },
  { delay: 2550, task: "3", sub: "3.1", status: "in-progress" },
  { delay: 3050, task: "3", sub: "3.1", status: "completed" },
  { delay: 3050, task: "3", sub: "3.2", status: "in-progress" },
  { delay: 3600, task: "3", sub: "3.2", status: "completed" },
  { delay: 3600, task: "3", sub: "3.3", status: "in-progress" },
  { delay: 4100, task: "3", sub: "3.3", status: "completed" },
  { delay: 4100, task: "3", status: "completed" },
  { delay: 4100, task: "4", status: "in-progress" },
  { delay: 4100, task: "4", sub: "4.1", status: "in-progress" },
  { delay: 4650, task: "4", sub: "4.1", status: "completed" },
  { delay: 4650, task: "4", sub: "4.2", status: "in-progress" },
  { delay: 5200, task: "4", sub: "4.2", status: "completed" },
  { delay: 5200, task: "4", sub: "4.3", status: "need-help" },
  { delay: 5200, task: "4", status: "need-help" },
];

function applyStatus(
  tasks: Task[],
  taskId: string,
  subId: string | undefined,
  status: Status
): Task[] {
  return tasks.map((t) => {
    if (t.id !== taskId) return t;
    if (!subId) return { ...t, status };
    return {
      ...t,
      subtasks: t.subtasks.map((s) => (s.id === subId ? { ...s, status } : s)),
    };
  });
}

let pending: ReturnType<typeof setTimeout>[] = [];
function clearPending() {
  pending.forEach((t) => clearTimeout(t));
  pending = [];
}

export const useAppStore = create<AppState>((set, get) => ({
  mode: "white",
  tasks: buildTasks(),

  trigger: () => {
    if (get().mode === "red") return;
    clearPending();
    set({ mode: "red" });
    DETECTION_CASCADE.forEach((u) => {
      const timer = setTimeout(() => {
        set((state) => ({
          tasks: applyStatus(state.tasks, u.task, u.sub, u.status),
        }));
      }, u.delay);
      pending.push(timer);
    });
  },

  standDown: () => {
    clearPending();
    set({ mode: "white", tasks: buildTasks() });
  },

  toggle: () => {
    if (get().mode === "white") get().trigger();
    else get().standDown();
  },
}));
