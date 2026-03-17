export type SocialGraphPersonProjection = {
  id: string;
  name: string;
  occurrenceCount: number;
};

export type SocialGraphLinkProjection = {
  personIds: [string, string];
  weight: number;
};

export type SocialGraphProjection = {
  persons: SocialGraphPersonProjection[];
  links: SocialGraphLinkProjection[];
};
