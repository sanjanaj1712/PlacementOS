-- Learning path catalog. Safe to run more than once.

insert into public.learning_paths (title, description, position) values
    ('Data Structures & Algorithms', 'Master the core topics required for technical interviews.', 1),
    ('Operating Systems', 'Core operating system concepts asked in technical interviews.', 2),
    ('Computer Networks', 'Networking fundamentals from the application layer down to the physical layer.', 3),
    ('DBMS', 'Database design, SQL, transactions and storage internals.', 4)
on conflict (title) do nothing;

insert into public.path_topics (learning_path_id, title, description, position)
select lp.id, t.title, t.description, t.position
from (values
    ('Data Structures & Algorithms', 'Arrays & Strings', 'Traversal, prefix sums, two pointers and sliding window techniques.', 1),
    ('Data Structures & Algorithms', 'Linked Lists', 'Singly and doubly linked lists, reversal, cycle detection and merging.', 2),
    ('Data Structures & Algorithms', 'Stacks & Queues', 'Monotonic stacks, queues, deques and their classic applications.', 3),
    ('Data Structures & Algorithms', 'Hashing', 'Hash maps and sets, frequency counting and collision handling.', 4),
    ('Data Structures & Algorithms', 'Trees', 'Binary trees, BSTs, traversals and lowest common ancestor.', 5),
    ('Data Structures & Algorithms', 'Graphs', 'BFS, DFS, topological sort, shortest paths and union-find.', 6),
    ('Data Structures & Algorithms', 'Dynamic Programming', 'Memoization, tabulation and common DP patterns.', 7),
    ('Data Structures & Algorithms', 'Sorting & Searching', 'Merge sort, quick sort, binary search and its variants.', 8),

    ('Operating Systems', 'Processes & Threads', 'Understand processes, threads, process states, and how they differ.', 1),
    ('Operating Systems', 'CPU Scheduling', 'Learn scheduling algorithms such as FCFS, SJF, Round Robin, and Priority Scheduling.', 2),
    ('Operating Systems', 'Process Synchronization', 'Learn critical sections, semaphores, mutexes, and synchronization problems.', 3),
    ('Operating Systems', 'Deadlocks', 'Understand deadlock conditions, prevention, avoidance, and detection.', 4),
    ('Operating Systems', 'Memory Management', 'Learn memory allocation, paging, segmentation, and address translation.', 5),
    ('Operating Systems', 'Virtual Memory', 'Understand virtual memory, page faults, demand paging, and page replacement.', 6),
    ('Operating Systems', 'File Systems', 'Learn file organization, directories, allocation methods, and file-system concepts.', 7),
    ('Operating Systems', 'I/O Systems', 'Understand I/O hardware, interrupts, buffering, and device management.', 8),

    ('Computer Networks', 'Network Fundamentals', 'Learn the basics of computer networks, protocols, network architecture, and the Internet.', 1),
    ('Computer Networks', 'Application Layer', 'Understand HTTP, DNS, email protocols, and how applications communicate over networks.', 2),
    ('Computer Networks', 'Transport Layer', 'Learn TCP, UDP, reliable data transfer, flow control, and congestion control.', 3),
    ('Computer Networks', 'Network Layer', 'Understand IP addressing, routing, forwarding, routing algorithms, and IPv4/IPv6.', 4),
    ('Computer Networks', 'Data Link Layer', 'Learn framing, error detection, MAC protocols, Ethernet, and switching.', 5),
    ('Computer Networks', 'Physical Layer', 'Understand how bits are transmitted through physical communication media.', 6),
    ('Computer Networks', 'Network Security', 'Learn the fundamentals of encryption, authentication, firewalls, and common network attacks.', 7),
    ('Computer Networks', 'Wireless & Mobile Networks', 'Understand Wi-Fi, wireless communication, mobility, and cellular networks.', 8),

    ('DBMS', 'DBMS Fundamentals', 'Learn database concepts, DBMS architecture, schemas, instances, and data models.', 1),
    ('DBMS', 'ER Model & Relational Model', 'Understand entities, relationships, keys, tables, and relational database concepts.', 2),
    ('DBMS', 'SQL', 'Practice SELECT, JOINs, subqueries, aggregation, grouping, and other SQL operations.', 3),
    ('DBMS', 'Normalization', 'Learn functional dependencies and normalization using 1NF, 2NF, 3NF, and BCNF.', 4),
    ('DBMS', 'Transactions', 'Understand transactions, ACID properties, schedules, and transaction states.', 5),
    ('DBMS', 'Concurrency Control', 'Learn locking, serializability, deadlocks, and techniques for managing concurrent transactions.', 6),
    ('DBMS', 'Indexing', 'Understand indexes, B+ trees, hashing, and how databases speed up queries.', 7),
    ('DBMS', 'Query Processing & Optimization', 'Learn how databases execute queries and optimize query execution plans.', 8)
) as t (path_title, title, description, position)
join public.learning_paths lp on lp.title = t.path_title
on conflict do nothing;

-- Subtopics
insert into public.path_topics (learning_path_id, parent_topic_id, title, description, position)
select parent.learning_path_id, parent.id, t.title, t.description, t.position
from (values
    ('Arrays & Strings', 'Two Pointers', 'Solve pair and partition problems in linear time.', 1),
    ('Arrays & Strings', 'Sliding Window', 'Fixed and variable size windows over arrays and strings.', 2),
    ('Graphs', 'BFS & DFS', 'Traversals, connected components and cycle detection.', 1),
    ('Graphs', 'Shortest Paths', 'Dijkstra, Bellman-Ford and 0-1 BFS.', 2),
    ('Dynamic Programming', '1D DP', 'Climbing stairs, house robber and similar problems.', 1),
    ('Dynamic Programming', '2D DP', 'Grid paths, LCS and edit distance.', 2)
) as t (parent_title, title, description, position)
join public.path_topics parent
    on parent.title = t.parent_title
    and parent.parent_topic_id is null
join public.learning_paths lp
    on lp.id = parent.learning_path_id
    and lp.title = 'Data Structures & Algorithms'
on conflict do nothing;
