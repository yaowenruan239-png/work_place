CREATE TABLE IF NOT EXISTS agent_error_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(64),
    task_type VARCHAR(64),
    user_query TEXT,
    tool_name VARCHAR(128),
    error_message TEXT,
    stack_trace TEXT,
    context_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experience_memories (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    problem_pattern TEXT NOT NULL,
    cause TEXT,
    solution TEXT NOT NULL,
    prompt_hint TEXT NOT NULL,
    importance INT DEFAULT 3,
    hit_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_vectors (
    memory_id BIGINT PRIMARY KEY,
    dim INT NOT NULL,
    vector_json JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_memory_vectors_memory_id
        FOREIGN KEY (memory_id)
        REFERENCES experience_memories(id)
        ON DELETE CASCADE
);
