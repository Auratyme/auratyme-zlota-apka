export type FindOneOptions<T> = {
  orderBy?: string;
  sortBy?: 'asc' | 'desc';
  where: T;
};
