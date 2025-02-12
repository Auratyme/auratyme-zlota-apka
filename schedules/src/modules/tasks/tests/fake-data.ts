import { Task } from '../types';

const fakeTaskIds = {
  FAKE_TASK_1_ID: 'd4764c24-97d7-406e-902c-783214a9a8c8',
  FAKE_TASK_2_ID: '675cc1a3-6965-462a-8945-fbe793c5a6d6',
  FAKE_TASK_3_ID: '9e4a94a2-1733-49f1-bd7e-06598c493e90',
  FAKE_TASK_4_ID: 'a5d8a2a6-c72e-4401-b975-7a994de75792',
  FAKE_TASK_5_ID: '6b2cbf97-ff40-40b7-b917-65626ff18da0',
  NON_EXISTENT_TASK_ID: 'fa808ebd-e31f-4903-921a-a16d656df778',
  FAKE_NEW_TASK_ID: '0d807195-df72-4ce7-b47b-24ae22b1c095',
};

const fakeTaskUserIds = {
  FAKE_TASK_1_USER_ID: '763e03da-6342-4927-b57e-e9067bd5dd25',
  FAKE_TASK_2_USER_ID: '86c27e3a-dba6-4436-b707-8f0a2a52ab04',
  FAKE_TASK_3_USER_ID: '4cb67df6-b107-4d0a-8867-bf8af22383d6',
  FAKE_TASK_4_USER_ID: '6d710866-209f-4e7c-820a-c98d1e7c94f5',
  FAKE_TASK_5_USER_ID: '9d7b051b-8b63-41aa-914d-0e5f33f0d288',
  NON_EXISTENT_TASK_USER_ID: '6a46b54e-974d-42b0-9c39-d43504ef8711',
  FAKE_NEW_TASK_USER_ID: '9d4e56c1-da8a-491b-8e52-dd9feffc345b',
};

const fakeTaskNames = {
  FAKE_TASK_1_NAME: 'task-1',
  FAKE_TASK_2_NAME: 'task-2',
  FAKE_TASK_3_NAME: 'task-3',
  FAKE_TASK_4_NAME: 'task-4',
  FAKE_TASK_5_NAME: 'task-5',
  NON_EXISTENT_TASK_NAME: 'non-existent',
  FAKE_NEW_TASK_NAME: 'new-task',
};

const fakeTasks: Task[] = [
  {
    id: fakeTaskIds.FAKE_TASK_1_ID,
    name: fakeTaskNames.FAKE_TASK_1_NAME,
    status: 'not-started',
    description: null,
    dueTo: '2025-01-18T19:00:00Z',
    repeat: null,
    createdAt: '2025-01-18T14:00:00Z',
    updatedAt: '2025-01-18T19:00:00Z',
    userId: fakeTaskUserIds.FAKE_TASK_1_USER_ID,
  },
  {
    id: fakeTaskIds.FAKE_TASK_2_ID,
    name: fakeTaskNames.FAKE_TASK_2_NAME,
    status: 'not-started',
    description: null,
    dueTo: '2025-01-18T19:00:00Z',
    repeat: null,
    createdAt: '2025-01-18T14:00:00Z',
    updatedAt: '2025-01-18T19:00:00Z',
    userId: fakeTaskUserIds.FAKE_TASK_2_USER_ID,
  },
  {
    id: fakeTaskIds.FAKE_TASK_3_ID,
    name: fakeTaskNames.FAKE_TASK_3_NAME,
    status: 'not-started',
    description: null,
    dueTo: '2025-01-18T19:00:00Z',
    repeat: null,
    createdAt: '2025-01-18T14:00:00Z',
    updatedAt: '2025-01-18T19:00:00Z',
    userId: fakeTaskUserIds.FAKE_TASK_3_USER_ID,
  },
  {
    id: fakeTaskIds.FAKE_TASK_4_ID,
    name: fakeTaskNames.FAKE_TASK_4_NAME,
    status: 'not-started',
    description: null,
    dueTo: '2025-01-18T19:00:00Z',
    repeat: null,
    createdAt: '2025-01-18T14:00:00Z',
    updatedAt: '2025-01-18T19:00:00Z',
    userId: fakeTaskUserIds.FAKE_TASK_4_USER_ID,
  },
  {
    id: fakeTaskIds.FAKE_TASK_5_ID,
    name: fakeTaskNames.FAKE_TASK_5_NAME,
    status: 'not-started',
    description: null,
    dueTo: '2025-01-18T19:00:00Z',
    repeat: null,
    createdAt: '2025-01-18T14:00:00Z',
    updatedAt: '2025-01-18T19:00:00Z',
    userId: fakeTaskUserIds.FAKE_TASK_5_USER_ID,
  },
];

export { fakeTaskIds, fakeTaskNames, fakeTaskUserIds, fakeTasks };
