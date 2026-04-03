export type PersonGroupColorOption = {
  index: number;
  label: string;
  color: string;
  softColor: string;
  borderColor: string;
  textColor: string;
};

export const PERSON_GROUP_COLOR_OPTIONS: PersonGroupColorOption[] = [
  {
    index: 1,
    label: "Amber",
    color: "#d97706",
    softColor: "rgba(217, 119, 6, 0.14)",
    borderColor: "rgba(217, 119, 6, 0.28)",
    textColor: "#8b4513",
  },
  {
    index: 2,
    label: "Moss",
    color: "#5f7a32",
    softColor: "rgba(95, 122, 50, 0.14)",
    borderColor: "rgba(95, 122, 50, 0.28)",
    textColor: "#405520",
  },
  {
    index: 3,
    label: "Teal",
    color: "#0f766e",
    softColor: "rgba(15, 118, 110, 0.14)",
    borderColor: "rgba(15, 118, 110, 0.28)",
    textColor: "#0f5c57",
  },
  {
    index: 4,
    label: "Sky",
    color: "#0369a1",
    softColor: "rgba(3, 105, 161, 0.14)",
    borderColor: "rgba(3, 105, 161, 0.28)",
    textColor: "#0f4c77",
  },
  {
    index: 5,
    label: "Rose",
    color: "#be185d",
    softColor: "rgba(190, 24, 93, 0.14)",
    borderColor: "rgba(190, 24, 93, 0.28)",
    textColor: "#8b1647",
  },
  {
    index: 6,
    label: "Plum",
    color: "#7c3aed",
    softColor: "rgba(124, 58, 237, 0.14)",
    borderColor: "rgba(124, 58, 237, 0.28)",
    textColor: "#5d2db3",
  },
];

export function getPersonGroupColorOption(
  colorIndex: number | null,
): PersonGroupColorOption | null {
  if (colorIndex === null) {
    return null;
  }

  return (
    PERSON_GROUP_COLOR_OPTIONS.find((option) => option.index === colorIndex) ??
    null
  );
}
