export type FindOptions<Where, OrderBy = string> = {
  limit?: number;
  page?: number;
  orderBy?: OrderBy;
  sortBy?: 'asc' | 'desc';
  where?: Where;
};
