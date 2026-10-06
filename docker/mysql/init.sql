CREATE DATABASE IF NOT EXISTS internship_monitor
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE internship_monitor;

CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    company VARCHAR(100) NOT NULL DEFAULT '',
    source VARCHAR(100) NOT NULL DEFAULT '',
    source_job_id VARCHAR(255) NOT NULL DEFAULT '',
    content_hash CHAR(64) NOT NULL DEFAULT '',
    title VARCHAR(500) NOT NULL DEFAULT '',
    city VARCHAR(255) NOT NULL DEFAULT '',
    country VARCHAR(255) NOT NULL DEFAULT '',
    department VARCHAR(255) NOT NULL DEFAULT '',
    category VARCHAR(255) NOT NULL DEFAULT '',
    salary VARCHAR(255) NOT NULL DEFAULT '',
    education VARCHAR(255) NOT NULL DEFAULT '',
    experience VARCHAR(255) NOT NULL DEFAULT '',
    description LONGTEXT,
    requirements LONGTEXT,
    job_type VARCHAR(100) NOT NULL DEFAULT '',
    publish_time VARCHAR(100) NOT NULL DEFAULT '',
    update_time VARCHAR(100) NOT NULL DEFAULT '',
    source_url VARCHAR(2048) NOT NULL DEFAULT '',
    crawl_time DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_source_job (source, source_job_id),
    INDEX idx_company (company),
    INDEX idx_city (city),
    INDEX idx_job_type (job_type),
    INDEX idx_source_job_id (source_job_id),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS favorites (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',
    job_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_favorite_user_job (user_id, job_id),
    INDEX idx_favorites_user (user_id),
    CONSTRAINT fk_favorite_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS job_embeddings (
    job_id BIGINT PRIMARY KEY,
    model VARCHAR(100) NOT NULL,
    dimension INT NOT NULL,
    content_hash CHAR(64) NOT NULL,
    embedding LONGTEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_embeddings_hash (content_hash),
    CONSTRAINT fk_embedding_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS monitor_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',
    name VARCHAR(200) NOT NULL,
    company VARCHAR(100) NOT NULL DEFAULT '',
    city VARCHAR(100) NOT NULL DEFAULT '',
    keyword VARCHAR(255) NOT NULL DEFAULT '',
    job_type VARCHAR(100) NOT NULL DEFAULT '',
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    last_checked_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_monitor_user (user_id),
    INDEX idx_monitor_enabled (enabled, last_checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS monitor_hits (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    monitor_id BIGINT NOT NULL,
    job_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notified_at DATETIME NULL,
    UNIQUE KEY uq_monitor_job (monitor_id, job_id),
    INDEX idx_hits_monitor (monitor_id, created_at),
    CONSTRAINT fk_hit_monitor FOREIGN KEY (monitor_id) REFERENCES monitor_configs(id) ON DELETE CASCADE,
    CONSTRAINT fk_hit_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
