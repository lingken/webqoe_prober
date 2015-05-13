#include <stdio.h>
#include <dirent.h>
#include <string.h>
#include <regex.h>

#include "uthash.h"
#include "utlist.h"

char path[] = "../format_data";
char site_name[256];
char category[256];
double p_category = 0;
double p_not_exist = 0;
char word[256];
double p_word = 0;

struct probability_dict
{
	char word[256];
	double probability;
	UT_hash_handle hh;
};

struct s_site_record
{
	double p_category_click;
	double p_category_object;
	double p_not_exist_click;
	double p_not_exist_object;
	struct probability_dict *p_dict_click;
	struct probability_dict *p_dict_object;
};

struct site_entry
{
	char site_name[256];
	struct s_site_record site_record;
	UT_hash_handle hh;
};

struct site_entry *site_hashtable = NULL;
struct site_entry *tmp_site_entry = NULL;

void read_file(const char *filename) {
	printf("A NEW FILE\n");
	FILE *fp = fopen(filename, "r");
	memset(site_name, 0, sizeof(site_name));
	memset(category, 0, sizeof(category));
	memset(word, 0, sizeof(word));
	fscanf(fp, "%s %s\n", site_name, category);
	printf("%s %s\n", site_name, category);
	fscanf(fp, "%lf %lf\n", &p_category, &p_not_exist);
	printf("%lf %lf\n", p_category, p_not_exist);

	struct site_entry *new_entry = NULL;
	HASH_FIND_STR(site_hashtable, site_name, new_entry);
	if (new_entry == NULL) {
		new_entry = malloc(sizeof(struct site_entry));
		memset(new_entry, 0, sizeof(struct site_entry));
		strncpy(new_entry->site_name, site_name, 256);
		HASH_ADD_STR(site_hashtable, site_name, new_entry);
	}
	if (category[0] == 'c') { // click
		(new_entry->site_record).p_category_click = p_category;
		(new_entry->site_record).p_not_exist_click = p_not_exist;

		while(fscanf(fp, "%s %lf\n", word, &p_word) != -1){
			printf("%s %lf\n", word, p_word);
			struct probability_dict *dict_entry;
			dict_entry = malloc(sizeof(struct probability_dict));
			memset(dict_entry, 0, sizeof(struct probability_dict));
			strncpy(dict_entry->word, word, 256);
			dict_entry->probability = p_word;
			HASH_ADD_STR((new_entry->site_record).p_dict_click, word, dict_entry);
		};
	} else { // object
		(new_entry->site_record).p_category_object = p_category;
		(new_entry->site_record).p_not_exist_object = p_not_exist;

		while(fscanf(fp, "%s %lf\n", word, &p_word) != -1){
			printf("%s %lf\n", word, p_word);
			struct probability_dict *dict_entry;
			dict_entry = malloc(sizeof(struct probability_dict));
			memset(dict_entry, 0, sizeof(struct probability_dict));
			strncpy(dict_entry->word, word, 256);
			dict_entry->probability = p_word;
			HASH_ADD_STR((new_entry->site_record).p_dict_object, word, dict_entry);
		};
	}
	printf("\n");
	fclose(fp);
}

void delete_site_hashtable() {
	// HASH_DEL(site_hashtable, tmp_site_entry);
	struct site_entry *current_site_entry;
	struct probability_dict *cur_dict_entry, *tmp_dict_entry;
	HASH_ITER(hh, site_hashtable, current_site_entry, tmp_site_entry) {
		HASH_DEL(site_hashtable, current_site_entry);

		HASH_ITER(hh, (current_site_entry->site_record).p_dict_click, cur_dict_entry, tmp_dict_entry) {
			HASH_DEL((current_site_entry->site_record).p_dict_click, cur_dict_entry);
			free(cur_dict_entry);
		}
		HASH_ITER(hh, (current_site_entry->site_record).p_dict_object, cur_dict_entry, tmp_dict_entry) {
			HASH_DEL((current_site_entry->site_record).p_dict_object, cur_dict_entry);
			free(cur_dict_entry);
		}

		free(current_site_entry);
	}
}

void display_all() {
	struct site_entry *current_site_entry;
	struct probability_dict *cur_dict_entry, *tmp_dict_entry;
	HASH_ITER(hh, site_hashtable, current_site_entry, tmp_site_entry) {
		printf("site name             : %s\n", current_site_entry->site_name);
		printf("    p_category_click  : %lf\n", (current_site_entry->site_record).p_category_click);
		printf("    p_category_object : %lf\n", (current_site_entry->site_record).p_category_object);
		printf("    p_not_exist_click : %lf\n", (current_site_entry->site_record).p_not_exist_click);
		printf("    p_not_exist_object: %lf\n", (current_site_entry->site_record).p_not_exist_object);
		printf("\n");
		printf("    p_click\n");
		HASH_ITER(hh, (current_site_entry->site_record).p_dict_click, cur_dict_entry, tmp_dict_entry) {
			printf("        %s %lf\n", cur_dict_entry->word, cur_dict_entry->probability);
		}
		printf("\n");
		printf("    p_object\n");
		HASH_ITER(hh, (current_site_entry->site_record).p_dict_object, cur_dict_entry, tmp_dict_entry) {
			printf("        %s %lf\n", cur_dict_entry->word, cur_dict_entry->probability);
		}
		printf("\n");

	}
}

// const char * pattern_domain_name = "([^/]*)/";
// no split in C regex?
char *keywords[10];
void separate_url(const char *url_string) {
	int len = strlen(url_string);
	int last = 0;
	int cur = 0;
	// {
	// 	int i = 0;
	// 	for (i = 0; i < 10; i ++) {
	// 		keywords[i] = malloc(256);
	// 	}
	// }
	int i = 0;
	for (i = 0; i < 10; i ++) {
		memset(keywords[i], 0, 256);
	}
	int word_cnt = 0;
	while (cur < len) {
		if (url_string[cur] == '.') {
			strncpy(keywords[word_cnt ++], url_string + last, cur - last);
			last = cur + 1;
		}
		if (url_string[cur] == '/') {
			strncpy(keywords[word_cnt ++], url_string + last, cur - last);
			last = cur + 1;
			break;
		}
		cur ++;
	}
	for (i = 0; i < 10; i ++) {
		printf("%s %d\n", keywords[i], strlen(keywords[i]));
	}
}

// -1 not a key site, 0 embedded object, 1 user click
int is_user_click() {
	int i = 0;
	struct site_entry *find_site_entry = NULL;
	for (i = 0; i < 10 && strlen(keywords[i]) != 0; i ++) {
		HASH_FIND_STR(site_hashtable, keywords[i], find_site_entry);
		if (find_site_entry != NULL) {
			break;
		}
	}
	if (find_site_entry == NULL) {
		return -1; // not a key site
	}
	double p_click = (find_site_entry->site_record).p_category_click;
	double p_object = (find_site_entry->site_record).p_category_object;
	for (i = 0; i < 10 && strlen(keywords[i]) != 0; i ++) {
		struct probability_dict *dict_entry = NULL;
		HASH_FIND_STR((find_site_entry->site_record).p_dict_click, keywords[i], dict_entry);
		if (dict_entry != NULL) {
			p_click *= dict_entry->probability;
		} else {
			p_click *= (find_site_entry->site_record).p_not_exist_click;
		}
		HASH_FIND_STR((find_site_entry->site_record).p_dict_object, keywords[i], dict_entry);
		if (dict_entry != NULL) {
			p_object *= dict_entry->probability;
		} else {
			p_object *= (find_site_entry->site_record).p_not_exist_object;
		}
	}
	if (p_click > p_object) {
		return 1; // user click
	} else {
		return 0; // embedded object
	}
}

int main() {
	int i = 0;
	for (i = 0; i < 10; i ++) {
		keywords[i] = malloc(256);
	}

	DIR           *dir;
	struct dirent *ent;
	dir = opendir(path);
	if (dir) {
	while ((ent = readdir(dir)) != NULL) {
		if (ent->d_type == 8) {
			char filename[256];
			memset(filename, 0, sizeof(filename));
			sprintf(filename, "%s/%s", path, ent->d_name);
			printf("%s\n", filename);

			read_file(filename);
		}
	}
	closedir(dir);
	}
	display_all();

	// separate_url("wwwwwwwww.sinasinasinasinasinasina.comcomcomcom.cn/");
	separate_url("www.lk.com.cn/");
	int rt = is_user_click(); printf("%d\n", rt);
	separate_url("wx.qq.com/");
	rt = is_user_click(); printf("%d\n", rt);
	separate_url("domain.cgi.qq.com/");
	rt = is_user_click(); printf("%d\n", rt);

	delete_site_hashtable();
	for (i = 0; i < 10; i ++) {
		free(keywords[i]);
	}
	return 0;
}