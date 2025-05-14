import { create } from './create'
import { find } from './find'
import { findOne } from './find-one'
import { deleteOne } from './delete-one'
import { updateOne } from './update-one'
import { findTasks } from './findTasks'
import { addTask } from './addTask'
import { removeTask } from './removeTask'

export const schedulesApi = {
  create, find, findOne, updateOne, deleteOne, findTasks, addTask, removeTask
}