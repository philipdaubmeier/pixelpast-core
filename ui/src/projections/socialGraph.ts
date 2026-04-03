export type SocialGraphPersonGroupProjection = {
  id: string;
  name: string;
  colorIndex: number | null;
};

export type SocialGraphPersonProjection = {
  id: string;
  name: string;
  occurrenceCount: number;
  matchingGroups: SocialGraphPersonGroupProjection[];
};

export type SocialGraphLinkProjection = {
  personIds: [string, string];
  weight: number;
  affinity: number;
};

export type SocialGraphProjection = {
  persons: SocialGraphPersonProjection[];
  links: SocialGraphLinkProjection[];
};
