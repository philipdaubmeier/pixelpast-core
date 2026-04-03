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
    label: "Sunlit clay",
    color: "#db9d47",
    softColor: "rgba(219, 157, 71, 0.14)",
    borderColor: "rgba(219, 157, 71, 0.28)",
    textColor: "#8b5e1a",
  },
  {
    index: 2,
    label: "Amerald",
    color: "#06ba63",
    softColor: "rgba(6, 186, 99, 0.14)",
    borderColor: "rgba(6, 186, 99, 0.28)",
    textColor: "#047647",
  },
  {
    index: 3,
    label: "Sky",
    color: "#06bee1",
    softColor: "rgba(6, 190, 225, 0.14)",
    borderColor: "rgba(6, 190, 225, 0.28)",
    textColor: "#0b6d83",
  },
  {
    index: 4,
    label: "Majorelle blue",
    color: "#574ae2",
    softColor: "rgba(87, 74, 226, 0.14)",
    borderColor: "rgba(87, 74, 226, 0.28)",
    textColor: "#3f33b7",
  },
  {
    index: 5,
    label: "Lobster",
    color: "#db5461",
    softColor: "rgba(219, 84, 97, 0.14)",
    borderColor: "rgba(219, 84, 97, 0.28)",
    textColor: "#9a2e39",
  },
  {
    index: 6,
    label: "Plum",
    color: "#f497da",
    softColor: "rgba(244, 151, 218, 0.14)",
    borderColor: "rgba(244, 151, 218, 0.28)",
    textColor: "#a84c8e",
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
