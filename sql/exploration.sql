-- List every task.
SELECT * FROM tasks;

-- Show only completed tasks.
SELECT * FROM tasks WHERE done = 1;

-- Count all tasks.
SELECT COUNT(*) AS total_tasks FROM tasks;

-- Mark every task as completed.
UPDATE tasks SET done = 1;

-- Delete all completed tasks.
DELETE FROM tasks WHERE done = 1;
