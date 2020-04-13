-- FETCH_USERS
CREATE OR REPLACE FUNCTION FETCH_USERS(page_size int = null, os int = null,
                                       search varchar = null,
                                       user_id int = null) RETURNS json AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
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
                                               ) AS profile,
                                               (
                                                   SELECT IS_FOLLOWING('auth_user', auth_user.id, user_id)
                                               ) AS is_following,
                                               (
                                                   SELECT array_to_json(array_agg(row_to_json(t)))
                                                   FROM (
                                                            SELECT publisher_publication.name,
                                                                   publisher_publication.id,
                                                                   (
                                                                       SELECT row_to_json(t)
                                                                       FROM (
                                                                                SELECT *,
                                                                                       (SELECT MAKE_THUMB(media_media.path)) as sizes
                                                                                FROM media_media
                                                                                WHERE publisher_publication.media_id = media_media.id
                                                                            ) t
                                                                       LIMIT 1
                                                                   ) AS media
                                                            FROM publisher_publication
                                                                     JOIN publisher_publication_writers
                                                                          ON publisher_publication_writers.publication_id = publisher_publication.id
                                                            WHERE publisher_publication_writers.user_id = auth_user.id
                                                        ) t
                                               ) as publications
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
                           )
                ) AS results,
                (
                    SELECT (
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
                                    ) t)
                ) AS count
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