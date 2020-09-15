-- CHAR_TO_INT
CREATE FUNCTION CHAR_TO_INT(character varying) RETURNS integer AS
$$
SELECT CASE
           WHEN length(btrim(regexp_replace($1, '[^0-9]', '', 'g'))) > 0
               THEN btrim(regexp_replace($1, '[^0-9]', '', 'g'))::integer
           ELSE 0
           END AS intval
$$
    LANGUAGE sql;

-- MAKE_THUMB
CREATE OR REPLACE FUNCTION MAKE_THUMB(path varchar) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/bubblask/',
                               path) AS full_size),
                (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/bubblask/cache/728x200/',
                               path) AS thumb_728_200),
                (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/bubblask/cache/96x96/',
                               path) AS thumb_96_96),
                (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/bubblask/cache/24x24/',
                               path) AS thumb_24_24)
     ) t
$$
    LANGUAGE sql;

-- FETCH_USERS
CREATE OR REPLACE FUNCTION FETCH_USERS(page_size int = null,
                                       os int = null,
                                       search varchar = null,
                                       user_id int = null) RETURNS json AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(f)))
                    FROM (
                             SELECT auth_user.id,
                                    auth_user.username,
                                    auth_user.first_name,
                                    auth_user.last_name,
                                    (
                                        SELECT row_to_json(t)
                                        FROM (
                                                 SELECT *,
                                                        (
                                                            SELECT row_to_json(u)
                                                            FROM (
                                                                     SELECT *,
                                                                            (SELECT MAKE_THUMB(md.path)) as sizes
                                                                     FROM media_media md
                                                                     WHERE md.id = dp.media_id
                                                                 ) u
                                                        ) AS media
                                                 FROM authentication_profile dp
                                                 WHERE dp.user_id = auth_user.id
                                             ) t
                                    ) AS profile
                             FROM auth_user
                             WHERE CASE
                                       WHEN FETCH_USERS.search is NOT NULL
                                           THEN
                                               auth_user.username LIKE LOWER(concat('%', FETCH_USERS.search, '%'))
                                               OR CONCAT(auth_user.first_name, ' ', auth_user.last_name) LIKE
                                                  LOWER(concat('%', FETCH_USERS.search, '%'))
                                       ELSE TRUE
                                       END
                             ORDER BY auth_user.id DESC
                             LIMIT page_size
                             OFFSET
                             os
                         ) f
                )             AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT auth_user.id
                             FROM auth_user
                             WHERE CASE
                                       WHEN FETCH_USERS.search is NOT NULL
                                           THEN
                                               auth_user.username LIKE LOWER(concat('%', FETCH_USERS.search, '%'))
                                               OR CONCAT(auth_user.first_name, ' ', auth_user.last_name) LIKE
                                                  LOWER(concat('%', FETCH_USERS.search, '%'))
                                       ELSE TRUE
                                       END
                             ORDER BY auth_user.date_joined DESC
                         ) t) AS count
     ) e
$$ LANGUAGE sql;

-- FETCH_USER_USERNAME
CREATE OR REPLACE FUNCTION FETCH_USER_USERNAME(x varchar) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT auth_user.id,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                (
                    SELECT row_to_json(t)
                    FROM (
                             SELECT *,
                                    (
                                        SELECT row_to_json(u)
                                        FROM (
                                                 SELECT *,
                                                        (SELECT MAKE_THUMB(md.path)) as sizes
                                                 FROM media_media md
                                                 WHERE md.id = dp.media_id
                                             ) u
                                    ) AS media
                             FROM authentication_profile dp
                             WHERE dp.user_id = auth_user.id
                         ) t
                ) AS profile
         FROM auth_user
         WHERE auth_user.username = x
     ) t
$$ LANGUAGE sql;

-- FETCH_USER_ID
CREATE OR REPLACE FUNCTION FETCH_USER_ID(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT auth_user.id,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                (
                    SELECT row_to_json(t)
                    FROM (
                             SELECT *,
                                    (
                                        SELECT row_to_json(u)
                                        FROM (
                                                 SELECT *,
                                                        (SELECT MAKE_THUMB(md.path)) as sizes
                                                 FROM media_media md
                                                 WHERE md.id = dp.media_id
                                             ) u
                                    ) AS media
                             FROM authentication_profile dp
                             WHERE dp.user_id = auth_user.id
                             LIMIT 1
                         ) t
                ) AS profile
         FROM auth_user
         WHERE auth_user.id = i
     ) t
$$ LANGUAGE sql;

-- FETCH_HASH_TAG
CREATE OR REPLACE FUNCTION FETCH_HASH_TAG(id int) RETURNS JSON AS
$$
SELECT row_to_json(t)
FROM (
         SELECT *
         FROM general_hashtag A
         WHERE A.id = FETCH_HASH_TAG.id
     ) t;

$$ LANGUAGE SQL;

-- FETCH_MEDIA
CREATE OR REPLACE FUNCTION FETCH_MEDIA(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT mm.id,
                (SELECT MAKE_THUMB(mm.path)) as sizes
         FROM media_media mm
         WHERE mm.id = i
         LIMIT 1
     ) t;

$$ LANGUAGE sql;

-- FETCH_TASKS
CREATE OR REPLACE FUNCTION FETCH_TASKS(page_size int = null,
                                       os int = null,
                                       search varchar = null,
                                       auth_id int = null,
                                       board_id int = null,
                                       statuses varchar[] = null,
                                       user_id int = null,
                                       parent_id int = null) RETURNS json AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT tt.*,
                                    (
                                        SELECT EXISTS(
                                                       SELECT tt2.id
                                                       FROM task_task tt2
                                                       WHERE tt2.parent_id = tt.id
                                                         AND tt2.status != 'STOPPED'
                                                         AND tt2.db_status = 1
                                                   )
                                    ) AS "has_child",
                                    (
                                        SELECT FETCH_USER_ID(tt.user_id)
                                    ) AS "user",
                                    (
                                        SELECT FETCH_USER_ID(tt.assignee_id)
                                    ) AS "assignee"
                             FROM task_task tt
                             WHERE tt.db_status = 1
                               AND CASE
                                       WHEN FETCH_TASKS.parent_id IS NOT NULL THEN
                                           FETCH_TASKS.parent_id = tt.parent_id
                                       ELSE tt.parent_id IS NULL END
                               AND CASE
                                       WHEN FETCH_TASKS.search IS NOT NULL THEN
                                               lower(tt.title) LIKE
                                               lower(concat('%', FETCH_TASKS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TASKS.board_id IS NOT NULL THEN
                                           tt.board_id = FETCH_TASKS.board_id
                                       ELSE CASE
                                                WHEN FETCH_TASKS.user_id IS NOT NULL THEN
                                                    tt.user_id = FETCH_TASKS.user_id
                                                ELSE FALSE END END
                               AND CASE
                                       WHEN FETCH_TASKS.statuses IS NOT NULL THEN
                                           tt.status = ANY (FETCH_TASKS.statuses)
                                       ELSE TRUE END
                             GROUP BY tt.id
                             LIMIT page_size
                             OFFSET
                             os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT tt.id
                             FROM task_task tt
                             WHERE tt.db_status = 1
                               AND CASE
                                       WHEN FETCH_TASKS.parent_id IS NOT NULL THEN
                                           FETCH_TASKS.parent_id = tt.parent_id
                                       ELSE tt.parent_id IS NULL END
                               AND CASE
                                       WHEN FETCH_TASKS.search IS NOT NULL THEN
                                               lower(tt.title) LIKE
                                               lower(concat('%', FETCH_TASKS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TASKS.board_id IS NOT NULL THEN
                                           tt.board_id = FETCH_TASKS.board_id
                                       ELSE CASE
                                                WHEN FETCH_TASKS.user_id IS NOT NULL THEN
                                                    tt.user_id = FETCH_TASKS.user_id
                                                ELSE FALSE END END
                               AND CASE
                                       WHEN FETCH_TASKS.statuses IS NOT NULL THEN
                                           tt.status = ANY (FETCH_TASKS.statuses)
                                       ELSE TRUE END
                         ) f
                ) AS count
     ) e
$$ LANGUAGE sql;

-- FETCH_BOARDS
CREATE OR REPLACE FUNCTION FETCH_BOARDS(page_size int = null,
                                        os int = null,
                                        search varchar = null,
                                        auth_id int = null,
                                        hash_tags integer[] = NULL,
                                        board_id int = NULL,
                                        kinds varchar[] = NULL,
                                        is_private boolean = NULL,
                                        user_id int = null) RETURNS json AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT tb.*,
                                    (
                                        SELECT FETCH_MEDIA(tb.media_id)
                                    ) AS "media",
                                    (
                                        SELECT COUNT(*)
                                        FROM (
                                                 SELECT id
                                                 FROM task_task tt
                                                 WHERE tt.board_id = tb.id
                                                   AND tt.db_status = 1
                                                   AND tb.parent_id IS NULL
                                             ) e
                                    ) as "task_count",
                                    (
                                        SELECT FETCH_USER_ID(tb.user_id)
                                    ) AS "user"
                             FROM task_board tb
                                      FULL JOIN task_board_hash_tags tbht on tb.id = tbht.board_id
                             WHERE tb.db_status = 1
                               AND CASE
                                       WHEN FETCH_BOARDS.search IS NOT NULL THEN
                                               lower(tb.title) LIKE
                                               lower(concat('%', FETCH_BOARDS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.board_id IS NOT NULL THEN
                                           tb.parent_id = FETCH_BOARDS.board_id
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.hash_tags IS NOT NULL
                                           THEN tbht.hashtag_id = ANY (FETCH_BOARDS.hash_tags)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.kinds IS NOT NULL
                                           THEN tb.kind = ANY (FETCH_BOARDS.kinds)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.is_private IS NOT NULL
                                           THEN tb.is_private = FETCH_BOARDS.is_private
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.user_id IS NOT NULL
                                           THEN tb.user_id = FETCH_BOARDS.user_id
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_BOARDS.auth_id IS NULL THEN
                                           cast(tb.settings ->> 'allow_search' AS BOOLEAN) = TRUE
                                       ELSE TRUE
                                 END
                             GROUP BY tb.id
                             LIMIT page_size
                             OFFSET
                             os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT tb.id
                             FROM task_board tb
                                      FULL JOIN task_board_hash_tags tbht on tb.id = tbht.board_id
                             WHERE tb.db_status = 1
                               AND CASE
                                       WHEN FETCH_BOARDS.search IS NOT NULL THEN
                                               lower(tb.title) LIKE
                                               lower(concat('%', FETCH_BOARDS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.board_id IS NOT NULL THEN
                                           tb.parent_id = FETCH_BOARDS.board_id
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.hash_tags IS NOT NULL
                                           THEN tbht.hashtag_id = ANY (FETCH_BOARDS.hash_tags)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.kinds IS NOT NULL
                                           THEN tb.kind = ANY (FETCH_BOARDS.kinds)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.is_private IS NOT NULL
                                           THEN tb.is_private = FETCH_BOARDS.is_private
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_BOARDS.user_id IS NOT NULL
                                           THEN tb.user_id = FETCH_BOARDS.user_id
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_BOARDS.auth_id IS NULL THEN
                                           cast(tb.settings ->> 'allow_search' AS BOOLEAN) = TRUE
                                       ELSE TRUE
                                 END
                             GROUP BY tb.id
                         ) f
                ) AS count
     ) e
$$ LANGUAGE sql;

-- FETCH_TASK
CREATE OR REPLACE FUNCTION FETCH_TASK(task_id int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT tt.*,
                (
                    SELECT EXISTS(
                                   SELECT tt2.id
                                   FROM task_task tt2
                                   WHERE tt2.parent_id = tt.id
                                     AND tt2.status != 'STOPPED'
                                     AND tt2.db_status = 1
                               )
                ) AS "has_child",
                (
                    SELECT FETCH_USER_ID(tt.user_id)
                ) AS "user",
                (
                    SELECT FETCH_USER_ID(tt.assignee_id)
                ) AS "assignee"
         FROM task_task tt
         WHERE tt.db_status = 1
           AND tt.id = task_id
         LIMIT 1
     ) t;

$$ LANGUAGE sql;

-- FETCH_BOARD
CREATE OR REPLACE FUNCTION FETCH_BOARD(board_id int = NULL, board_slug varchar = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT tb.*,
                (
                    SELECT FETCH_USER_ID(tb.user_id)
                ) AS "user",
                (
                    SELECT FETCH_MEDIA(tb.media_id)
                ) AS "media"
         FROM task_board tb
         WHERE tb.db_status = 1
           AND CASE
                   WHEN board_id IS NOT NULL THEN tb.id = board_id
                   ELSE CASE WHEN board_slug IS NOT NULL THEN tb.slug = board_slug ELSE FALSE END END
         LIMIT 1
     ) t;

$$ LANGUAGE sql;

-- FETCH_MEMBERS
CREATE OR REPLACE FUNCTION FETCH_MEMBERS(page_size int = null,
                                         os int = null,
                                         search varchar = null,
                                         user_id int = null,
                                         board_id int = null) RETURNS json AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(f)))
                    FROM (
                             SELECT tbm.id,
                                    (SELECT FETCH_USER_ID(tbm.user_id))      AS "user",
                                    (SELECT FETCH_BOARD(tbm.board_id, NULL)) AS "board"
                             FROM task_boardmember tbm
                             WHERE CASE
                                       WHEN FETCH_MEMBERS.search is NOT NULL
                                           THEN
                                           FALSE
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_MEMBERS.user_id is NOT NULL
                                           THEN tbm.user_id = FETCH_MEMBERS.user_id
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_MEMBERS.board_id is NOT NULL
                                           THEN tbm.board_id = FETCH_MEMBERS.board_id
                                       ELSE TRUE
                                 END
                             ORDER BY tbm.id DESC
                             LIMIT page_size
                             OFFSET
                             os
                         ) f
                )             AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT tbm.id
                             FROM task_boardmember tbm
                             WHERE CASE
                                       WHEN FETCH_MEMBERS.search is NOT NULL
                                           THEN
                                           FALSE
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_MEMBERS.user_id is NOT NULL
                                           THEN tbm.user_id = FETCH_MEMBERS.user_id
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_MEMBERS.board_id is NOT NULL
                                           THEN tbm.board_id = FETCH_MEMBERS.board_id
                                       ELSE TRUE
                                 END
                         ) t) AS count
     ) e
$$ LANGUAGE sql;
