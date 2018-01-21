#define ADS_MAX_ERROR_LEN        600

/* Error codes */
#define AE_TRANS_OUT_OF_SEQUENCE        5047
#define AE_VALUE_OVERFLOW               5179

struct a_ads_connection {
   uint64_t handle;  // Real ADS connection, set via ads_connect
};
struct a_ads_stmt;

enum a_ads_data_type {
    A_INVALID_TYPE,
    A_BINARY,
    A_STRING,
    A_DOUBLE,
    A_VAL64,
    A_UVAL64,
    A_VAL32,
    A_UVAL32,
    A_VAL16,
    A_UVAL16,
    A_VAL8,
    A_UVAL8,
    A_NCHAR,
    A_DECIMAL,
    A_DATE,
    A_TIME,
    A_TIMESTAMP
};

struct a_ads_data_value {
    char *buffer;
    unsigned int buffer_size;
    unsigned int *length;
    enum a_ads_data_type type;
    unsigned int *is_null;
};

enum a_ads_data_direction
{
    DD_INVALID = 0x0,
    DD_INPUT = 0x1,
    DD_OUTPUT = 0x2,
    DD_INPUT_OUTPUT = 0x3
};

struct a_ads_bind_param {
    enum a_ads_data_direction direction;
    struct a_ads_data_value value;
    char *name;
};

enum a_ads_native_type {
    DT_NOTYPE = 0,
    DT_DATE = 384,
    DT_TIME = 388,
    DT_TIMESTAMP = 392,
    DT_VARCHAR = 448,
    DT_FIXCHAR = 452,
    DT_LONGVARCHAR = 456,
    DT_STRING = 460,
    DT_DOUBLE = 480,
    DT_FLOAT = 482,
    DT_DECIMAL = 484,
    DT_INT = 496,
    DT_SMALLINT = 500,
    DT_BINARY = 524,
    DT_LONGBINARY = 528,
    DT_TINYINT = 604,
    DT_BIGINT = 608,
    DT_UNSINT = 612,
    DT_UNSSMALLINT = 616,
    DT_UNSBIGINT = 620,
    DT_BIT = 624,
    DT_NSTRING = 628,
    DT_NFIXCHAR = 632,
    DT_NVARCHAR = 636,
    DT_LONGNVARCHAR = 640
};

struct a_ads_column_info {
    char *name;
    enum a_ads_data_type type;
    enum a_ads_native_type native_type;
    unsigned short int precision;
    unsigned short int scale;
    unsigned int max_size;
    unsigned int nullable;
};

int ads_init(const char *app_name, unsigned int api_version,
		unsigned int *version_availble);
void ads_fini(void);
struct a_ads_connection *ads_new_connection(void);
void ads_free_connection(struct a_ads_connection *ads_conn);
int ads_connect(struct a_ads_connection *ads_conn, const char *str);
int ads_disconnect(struct a_ads_connection *ads_conn);
int ads_commit(struct a_ads_connection *ads_conn);
int ads_rollback(struct a_ads_connection *ads_conn);
int ads_error(struct a_ads_connection *ads_conn, char *buffer, size_t size);
void ads_clear_error(struct a_ads_connection *ads_conn);

struct a_ads_stmt *ads_prepare(struct a_ads_connection *ads_conn,
		const char *sql_str, int);
void ads_free_stmt(struct a_ads_stmt *ads_stmt);
int ads_num_params(struct a_ads_stmt *ads_stmt);
int ads_describe_bind_param(struct a_ads_stmt *ads_stmt, unsigned int index,
		struct a_ads_bind_param *param);
int ads_bind_param(struct a_ads_stmt *ads_stmt, unsigned int index,
		struct a_ads_bind_param *param);
int ads_execute(struct a_ads_stmt *ads_stmt);
int ads_fetch_next(struct a_ads_stmt *ads_stmt);
int ads_affected_rows(struct a_ads_stmt *ads_stmt);
int ads_num_cols(struct a_ads_stmt *ads_stmt);
int ads_num_rows(struct a_ads_stmt *ads_stmt);
int ads_get_column(struct a_ads_stmt *ads_stmt, unsigned int col_index,
		struct a_ads_data_value *buffer);
int ads_get_column_info(struct a_ads_stmt *ads_stmt, unsigned int col_index,
		struct a_ads_column_info *buffer);

/* Advantage Client Engine Transaction Processing APIs */
unsigned int AdsBeginTransaction(uint64_t handle);
unsigned int AdsInTransaction(uint64_t handle, unsigned short int *in_trans);
unsigned int AdsGetTransactionCount(uint64_t handle, unsigned int *count);
