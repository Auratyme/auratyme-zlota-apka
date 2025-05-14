export type Task = {
  id: string;
  name: string;
  description: string | null;
  dueTo: string | null;
  repeat: string | null;
  userId: string;
  createdAt: string;
  updatedAt: string;
};
