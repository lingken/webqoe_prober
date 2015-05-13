#include <pcap.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <regex.h>
#include <netinet/if_ether.h>

#include "uthash.h"
#include "utlist.h"

#define false 0
#define SNAP_LEN 1518
#define REF_EXPIRE 5
#define FILE_EXPIRE 60
#define PACKET_NUMBER 40000
// EXPIRE in seconds
pcap_t *handle;
/* on OpenWrt */
char dev[256] = "eth1";
/* on my computer */
// char dev[] = "en0";
char errbuf[PCAP_ERRBUF_SIZE];
struct bpf_program fp;
char filter_exp[] = "port 80";
bpf_u_int32 mask;
bpf_u_int32 net;
struct pcap_pkthdr header;
const u_char *packet;

int c_get = 0;
int c_match = 0;
/* Ethernet addresses are 6 bytes */
#define ETHER_ADDR_LEN	6

/* Ethernet header */
struct sniff_ethernet {
	// u_char ether_dhost[ETHER_ADDR_LEN]; /* Destination host address */
	// u_char ether_shost[ETHER_ADDR_LEN]; /* Source host address */
	struct ether_addr ether_dhost;
	struct ether_addr ether_shost;
	u_short ether_type; /* IP? ARP? RARP? etc */
};

/* IP header */
struct sniff_ip {
	u_char ip_vhl;		/* version << 4 | header length >> 2 */
	u_char ip_tos;		/* type of service */
	u_short ip_len;		/* total length */
	u_short ip_id;		/* identification */
	u_short ip_off;		/* fragment offset field */
	#define IP_RF 0x8000		/* reserved fragment flag */
	#define IP_DF 0x4000		/* dont fragment flag */
	#define IP_MF 0x2000		/* more fragments flag */
	#define IP_OFFMASK 0x1fff	/* mask for fragmenting bits */
	u_char ip_ttl;		/* time to live */
	u_char ip_p;		/* protocol */
	u_short ip_sum;		/* checksum */
	struct in_addr ip_src,ip_dst; /* source and dest address */
};
#define IP_HL(ip)		(((ip)->ip_vhl) & 0x0f)
#define IP_V(ip)		(((ip)->ip_vhl) >> 4)

/* TCP header */
typedef u_int tcp_seq;

struct sniff_tcp {
	u_short th_sport;	/* source port */
	u_short th_dport;	/* destination port */
	tcp_seq th_seq;		/* sequence number */
	tcp_seq th_ack;		/* acknowledgement number */
	u_char th_offx2;	/* data offset, rsvd */
	#define TH_OFF(th)	(((th)->th_offx2 & 0xf0) >> 4)
	u_char th_flags;
	#define TH_FIN 0x01
	#define TH_SYN 0x02
	#define TH_RST 0x04
	#define TH_PUSH 0x08
	#define TH_ACK 0x10
	#define TH_URG 0x20
	#define TH_ECE 0x40
	#define TH_CWR 0x80
	#define TH_FLAGS (TH_FIN|TH_SYN|TH_RST|TH_ACK|TH_URG|TH_ECE|TH_CWR)
	u_short th_win;		/* window */
	u_short th_sum;		/* checksum */
	u_short th_urp;		/* urgent pointer */
};

/* ethernet headers are always exactly 14 bytes */
#define SIZE_ETHERNET 14

/* My own string cat function */
#define STRING_LENGTH 256
#define SAFE_LENGTH (STRING_LENGTH - 1)
void my_strcat(char *dst, const char *str1, const char *str2) {
	int len1 = strlen(str1);
	if (len1 >= SAFE_LENGTH) {
		strncpy(dst, str1, SAFE_LENGTH);
		return;
	} else {
		strncpy(dst, str1, len1);
	}
	int n = SAFE_LENGTH - len1;
	strncpy(dst + len1, str2, n);
	return;
}

/* Construct the dict and link list */

typedef struct packet_record {
	char GET[STRING_LENGTH];
	char Host[STRING_LENGTH];
	char User_Agent[STRING_LENGTH];
	char Referer[STRING_LENGTH];
	struct timeval timestamp;
	char IP_src[20];
	char dev_MAC[20];

} packet_record;

packet_record *new_packet_record() {
	packet_record *p_record;
	p_record = malloc(sizeof(packet_record));
	memset(p_record, 0, sizeof(p_record));
	return p_record;
}

/* Construct the record queue */
typedef struct record_queue
{
	struct packet_record *p_record;
	struct record_queue *next;
} record_queue;

struct record_queue *base, *tail;

void add_to_record_queue(packet_record *p_record) {
	record_queue *p_queue_elem = malloc(sizeof(record_queue));
	memset(p_queue_elem, 0, sizeof(record_queue));

	p_queue_elem->p_record = p_record;
	tail->next = p_queue_elem;
	tail = tail->next;
}

record_queue* get_from_record_queue() {
	record_queue *p_queue_elem = NULL;
	if ((p_queue_elem = base->next) != NULL) {
		base->next = p_queue_elem->next;
	}
	return p_queue_elem;
}

void initialize_record() {
	base = NULL;
	tail = NULL;

	base = malloc(sizeof(record_queue));
	memset(base, 0, sizeof(record_queue));
	base->p_record = NULL;
	base->next = NULL;
	tail = base;
}

/* File process */
FILE *filepointer = NULL;
// struct timeval time_filecreate;

/* Work with Regular Expression here */
// pattern with Referer
/*
	pm[1] GET
	pm[2] Host
	pm[3] User-Agent
	pm[5] Referer
	[pm[i].rm_so, pm[i].rm_eo)
	e.g: find bcd from abcde
	rm_so = 1, rm_eo = 4
*/
// const char * pattern_r = "GET (.*) HTTP.*Host: (.*)\r\nConnection:.*User-Agent: (.*)\r\n(X-Reque.*)?DNT:.*(Referer: (.*)\r\n)?Accept-Enco";

// const char * pattern_r = "GET (.*) HTTP[^\r\n]*\r\nHost: ([^\r\n]*)\r\n.*User-Agent: ([^\r\n]*)\r\n.*DNT:[^\r\n]*\r\n(Referer: ([^\r\n]*)\r\n)?Accept-Enco";
// regex_t reg_r;

const char * pattern_GET = "GET (.*) HTTP";
const char * pattern_Host = ".*Host: ([^\r\n]*)\r\n";
const char * pattern_User_Agent = ".*User-Agent: ([^\r\n]*)\r\n";
const char * pattern_Referer = ".*Referer: ([^\r\n]*)\r\n";

regex_t reg_GET;
regex_t reg_Host;
regex_t reg_User_Agent;
regex_t reg_Referer;

regmatch_t pm[10];
const int nmatch = 10;

void initialize_regex() {
	// if (regcomp(&reg_r, pattern_r, REG_EXTENDED) != 0){
	// 	fprintf(stderr, "%s\n", "regcomp error");
	// }
	if (regcomp(&reg_GET, pattern_GET, REG_EXTENDED) != 0){
		fprintf(stderr, "%s\n", "regcomp error");
	}
	if (regcomp(&reg_Host, pattern_Host, REG_EXTENDED) != 0){
		fprintf(stderr, "%s\n", "regcomp error");
	}
	if (regcomp(&reg_User_Agent, pattern_User_Agent, REG_EXTENDED) != 0){
		fprintf(stderr, "%s\n", "regcomp error");
	}
	if (regcomp(&reg_Referer, pattern_Referer, REG_EXTENDED) != 0){
		fprintf(stderr, "%s\n", "regcomp error");
	}
}

char GET[STRING_LENGTH];
char Host[STRING_LENGTH];
char User_Agent[STRING_LENGTH];
char Referer[STRING_LENGTH];
void match_payload(const char *payload, int packet_no, const struct pcap_pkthdr *pcap_header, const struct sniff_ip *ip_header, const struct sniff_ethernet *ethernet) {
	memset(GET, 0, STRING_LENGTH);
	memset(Host, 0, STRING_LENGTH); // if there isn't the func, Host will be corrupted, but why
	memset(User_Agent, 0, STRING_LENGTH);
	memset(Referer, 0, STRING_LENGTH);
	int b_get = 0;
	if (payload[0] == 'G' && payload[1] == 'E' && payload[2] == 'T'){
		c_get ++;
		b_get = 1;
	}

	if (regexec(&reg_GET, payload, nmatch, pm, 0) == 0) {
		int n_GET = (int)(pm[1].rm_eo - pm[1].rm_so);
		strncpy(GET, payload + pm[1].rm_so, n_GET < SAFE_LENGTH ? n_GET : SAFE_LENGTH);

		int n_Host = 0;
		int n_User_Agent = 0;
		int n_Referer = 0;

		if (regexec(&reg_Host, payload, nmatch, pm, 0) == 0) {
			n_Host = (int)(pm[1].rm_eo - pm[1].rm_so);
			strncpy(Host, payload + pm[1].rm_so, n_Host < SAFE_LENGTH ? n_Host : SAFE_LENGTH);
		} else {
			return;
		}
		if (regexec(&reg_User_Agent, payload, nmatch, pm, 0) == 0) {
			n_User_Agent = (int)(pm[1].rm_eo - pm[1].rm_so);
			strncpy(User_Agent, payload + pm[1].rm_so, n_User_Agent < SAFE_LENGTH ? n_User_Agent : SAFE_LENGTH);
		} else {
			return;
		}
		printf("shost: %s, dhost: %s\n", ether_ntoa(&ethernet->ether_shost), ether_ntoa(&ethernet->ether_dhost));
		printf("Packet number: %d\n", packet_no);
		printf("          GET: %s\n", GET);
		printf("         Host: %s\n", Host);
		printf("   User-Agent: %s\n", User_Agent);

		// printf("Packet number: %d\n", packet_no);
		// printf("          GET: %.*s\n", n_GET, payload + pm[1].rm_so);
		// printf("         Host: %.*s\n", n_Host, payload + pm[2].rm_so);
		// printf("   User-Agent: %.*s\n", n_User_Agent, payload + pm[3].rm_so);
		if (regexec(&reg_Referer, payload, nmatch, pm, 0) == 0) {
			/* Use the referer to find in the dict, if exist, add Get + Host as a new referer */
			n_Referer = (int)(pm[1].rm_eo - pm[1].rm_so);
			strncpy(Referer, payload + pm[1].rm_so, n_Referer < SAFE_LENGTH ? n_Referer : SAFE_LENGTH);
		} else {
			strncpy(Referer, "NULL", SAFE_LENGTH);
		}
		printf("      Referer: %s\n", Referer);
		printf("\n");

		packet_record *p_record = new_packet_record();
		strncpy(p_record->GET, GET, SAFE_LENGTH);
		strncpy(p_record->Host, Host, SAFE_LENGTH);
		strncpy(p_record->User_Agent, User_Agent, SAFE_LENGTH);
		strncpy(p_record->Referer, Referer, SAFE_LENGTH);
		strncpy(p_record->IP_src, inet_ntoa(ip_header->ip_src), 20);
		p_record->timestamp = pcap_header->ts;

		add_to_record_queue(p_record);

		c_match ++;
		// check_to_delete();
	}
}

void display_packet_record(packet_record *p_record) {
	printf("time: %d + %d\n", (p_record->timestamp).tv_sec, (p_record->timestamp).tv_usec);
	printf("IP src: %s\n", p_record->IP_src);
	printf("dev MAC: %s\n", p_record->dev_MAC);
	printf("GET: %s\n", p_record->GET);
	printf("Host: %s\n", p_record->Host);
	printf("User-Agent: %s\n", p_record->User_Agent);
	printf("Referer: %s\n", p_record->Referer);
	printf("\n");
}

void write_packet_record_to_file(packet_record *p_record) {
	fprintf(filepointer, "time: %d + %d, IP src: %s, dev MAC: %s, GET: %s, Host: %s, User-Agent: %s, Referer: %s\n", 
		(p_record->timestamp).tv_sec, (p_record->timestamp).tv_usec,
		p_record->IP_src,
		p_record->dev_MAC,
		p_record->GET,
		p_record->Host,
		p_record->User_Agent,
		p_record->Referer);
}

void delete_and_free_all() {
	record_queue *p_queue_elem = NULL;
	while ((p_queue_elem = get_from_record_queue()) != NULL) {
		packet_record *p_record = p_queue_elem->p_record;
		// display_packet_record(p_record);
		write_packet_record_to_file(p_record);
		free(p_record);
		free(p_queue_elem);
	}
}

void process_packet(u_char *args, const struct pcap_pkthdr *header, const u_char *packet) {
	static int count = 0;
	count ++;

	const struct sniff_ethernet *ethernet; /* The ethernet header */
	const struct sniff_ip *ip; /* The IP header */
	const struct sniff_tcp *tcp; /* The TCP header */
	const char *payload; /* Packet payload */

	u_int size_ip;
	u_int size_tcp;

	ethernet = (struct sniff_ethernet*)(packet);

	ip = (struct sniff_ip*)(packet + SIZE_ETHERNET);
	size_ip = IP_HL(ip)*4;
	if (size_ip < 20) {
		// printf("   * Invalid IP header length: %u bytes\n", size_ip);
		return;
	}
	tcp = (struct sniff_tcp*)(packet + SIZE_ETHERNET + size_ip);
	size_tcp = TH_OFF(tcp)*4;
	if (size_tcp < 20) {
		// printf("   * Invalid TCP header length: %u bytes\n", size_tcp);
		return;
	}
	payload = (u_char *)(packet + SIZE_ETHERNET + size_ip + size_tcp);

	match_payload(payload, count, header, ip, ethernet);
}

int main(int argc, char *argv[])
{
	// argv[1] - MAC, argv[2] - dev
	if (argc < 3) {
		fprintf(stderr, "Not enough arg number, no MAC addr or interface name.\n");
		return(2);
	}
	memset(dev, 0, sizeof(dev));
	strncpy(dev, argv[2], 256);

	printf("%s\n", "Hello World!");
	if (pcap_lookupnet(dev, &net, &mask, errbuf) == -1) {
		fprintf(stderr, "Can't get netmask for device %s\n", dev);
		net = 0;
		mask = 0;
	}
	handle = pcap_open_live (dev, BUFSIZ, false, 1000, errbuf);
	if (handle == NULL) {
		fprintf(stderr, "Couldn't open device %s: %s\n", dev, errbuf);
		return(2);
	}
	if (pcap_datalink(handle) != DLT_EN10MB) {
		fprintf(stderr, "Device %s doesn't provide Ethernet headers - not supported\n", dev);
		return(2);
	}
	if (pcap_compile(handle, &fp, filter_exp, 0, net) == -1) {
		fprintf(stderr, "Couldn't parse filter %s: %s\n", filter_exp, pcap_geterr(handle));
		return(2);
	}
	if (pcap_setfilter(handle, &fp) == -1) {
		fprintf(stderr, "Couldn't install filter %s: %s\n", filter_exp, pcap_geterr(handle));
		return(2);
	}

	initialize_regex();
	initialize_record();
	pcap_loop(handle, PACKET_NUMBER, process_packet, NULL);

	printf("Packet Capture Complete\n");
	
	char filename[256];
	memset(filename, 0, sizeof(filename));
	struct timeval current;
	gettimeofday(&current, NULL);
	// sprintf(filename, "/root/webqoe/%s/%d.txt", argv[1], current.tv_sec);
	sprintf(filename, "tmptrace.txt");
	filepointer = fopen(filename, "w");

	delete_and_free_all();

	printf("  Get number: %d\n", c_get);
	printf("Match number: %d\n", c_match);

	fprintf(filepointer, "  Get number: %d\n", c_get);
	fprintf(filepointer, "Match number: %d\n", c_match);

	// fclose(filepointer);
	free(base);

	pcap_freecode(&fp);
	pcap_close(handle);
	
	return(0);
}