import { create } from './create'
import { find } from './find'
import { findOne } from './find-one'
import { deleteOne } from './delete-one'
import { updateOne } from './update-one'

export const tasksApi = {
  create, find, findOne, updateOne, deleteOne
}