import json
import csv
import re
from collections import defaultdict, Counter

def run_match():
    tutors_path = "Tutors/scraped_tutors.json"
    contacts_path = "nsu_directory_contacts.json"

    with open(tutors_path, "r", encoding="utf-8") as f:
        tutors_data = json.load(f)

    with open(contacts_path, "r", encoding="utf-8") as f:
        contacts_data = json.load(f)

    # Extract unique commentators preserving order
    unique_commentators = []
    seen_comms = set()
    for post in tutors_data:
        for comm in post.get("commentators", []):
            c = comm.strip()
            if c and c not in seen_comms:
                seen_comms.add(c)
                unique_commentators.append(c)

    prefix_map = {
        "md": "mohammad",
        "mohd": "mohammad",
        "mohammed": "mohammad",
        "muhammad": "mohammad",
        "mst": "most",
    }

    def clean_tokens(s):
        s = re.sub(r'\b\d+\b', '', s)
        s = re.sub(r'[^a-zA-Z\s]', ' ', s)
        return s.lower().split()

    def normalize_name_string(s):
        return ' '.join(clean_tokens(s))

    def canonical_tokens(s):
        tokens = clean_tokens(s)
        return [prefix_map.get(t, t) for t in tokens]

    contacts = []
    exact_dict = defaultdict(list)
    token_dict = defaultdict(list)

    for idx, c in enumerate(contacts_data):
        raw_name = c.get("name", "").strip()
        email = c.get("email", "").strip().lower()
        norm_str = normalize_name_string(raw_name)
        canon_toks = canonical_tokens(raw_name)
        canon_set = set(canon_toks)
        canon_str = ' '.join(canon_toks)

        contact_obj = {
            "idx": idx,
            "name": raw_name,
            "email": email,
            "norm_str": norm_str,
            "canon_toks": canon_toks,
            "canon_set": canon_set,
            "canon_str": canon_str
        }
        contacts.append(contact_obj)

        if norm_str:
            exact_dict[norm_str].append(contact_obj)
        if canon_str != norm_str:
            exact_dict[canon_str].append(contact_obj)

        for tok in canon_set:
            if len(tok) >= 2:
                token_dict[tok].append(idx)

    output_records = []
    status_by_comm = {}

    for comm in unique_commentators:
        comm_norm = normalize_name_string(comm)
        comm_canon = canonical_tokens(comm)
        comm_canon_set = set(comm_canon)
        comm_canon_str = ' '.join(comm_canon)

        # 1. Full Match Check
        full_hits = exact_dict.get(comm_norm, [])
        if not full_hits and comm_canon_str != comm_norm:
            full_hits = exact_dict.get(comm_canon_str, [])

        if full_hits:
            status_by_comm[comm] = "fully matched"
            seen_emails = set()
            for hit in full_hits:
                if hit["email"] not in seen_emails:
                    seen_emails.add(hit["email"])
                    output_records.append({
                        "name": comm,
                        "matched_contact_name": hit["name"],
                        "email": hit["email"],
                        "address": hit["email"],
                        "matched_condition": "fully matched"
                    })
            continue

        # 2. Partial Match Check
        if not comm_canon:
            status_by_comm[comm] = "not matched"
            output_records.append({
                "name": comm,
                "matched_contact_name": "N/A",
                "email": "N/A",
                "address": "N/A",
                "matched_condition": "not matched"
            })
            continue

        candidate_counts = defaultdict(int)
        for tok in comm_canon_set:
            for c_idx in token_dict.get(tok, []):
                candidate_counts[c_idx] += 1

        comm_concat = "".join(comm_canon)
        partial_hits = []
        sig_comm_tokens = [t for t in comm_canon if t not in ('md', 'mohammad', 'islam', 'ahmed', 'hossain', 'rahman', 'chowdhury', 'khan', 'akter', 'khatun') and len(t) > 2]

        for c_idx in candidate_counts:
            c = contacts[c_idx]
            c_toks = c['canon_set']

            # A. All commentator tokens in contact
            if comm_canon_set.issubset(c_toks):
                partial_hits.append(c)
            # B. All contact tokens in commentator (contact >= 2 tokens)
            elif len(c_toks) >= 2 and c_toks.issubset(comm_canon_set):
                partial_hits.append(c)
            # C. Concatenated match (e.g. debnath == deb nath)
            elif comm_concat and comm_concat == "".join(c['canon_toks']):
                partial_hits.append(c)
            # D. Non-prefix subset or 2+ significant tokens match
            elif len(comm_canon) >= 2:
                non_prefix = [t for t in comm_canon if t not in ('mohammad', 'mst', 'syed')]
                if len(non_prefix) >= 2 and set(non_prefix).issubset(c_toks):
                    partial_hits.append(c)
                elif len(sig_comm_tokens) >= 2 and set(sig_comm_tokens).issubset(c_toks):
                    partial_hits.append(c)
            # E. Single-word name match
            elif len(comm_canon) == 1:
                tok = comm_canon[0]
                if tok in c_toks and len(tok) > 2:
                    partial_hits.append(c)

        if partial_hits:
            status_by_comm[comm] = "partially matched"
            seen_emails = set()
            for hit in partial_hits:
                if hit["email"] not in seen_emails:
                    seen_emails.add(hit["email"])
                    output_records.append({
                        "name": comm,
                        "matched_contact_name": hit["name"],
                        "email": hit["email"],
                        "address": hit["email"],
                        "matched_condition": "partially matched"
                    })
        else:
            status_by_comm[comm] = "not matched"
            output_records.append({
                "name": comm,
                "matched_contact_name": "N/A",
                "email": "N/A",
                "address": "N/A",
                "matched_condition": "not matched"
            })

    # Save to JSON and CSV
    out_files = [
        "matched_commentators.json",
        "Tutors/matched_commentators.json"
    ]
    for p in out_files:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(output_records, f, indent=2, ensure_ascii=False)

    csv_files = [
        "matched_commentators.csv",
        "Tutors/matched_commentators.csv"
    ]
    for p in csv_files:
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "email", "address", "matched_condition", "matched_contact_name"])
            writer.writeheader()
            writer.writerows(output_records)

    stats = Counter(status_by_comm.values())
    print(f"Commentators processed: {len(unique_commentators)}")
    print(f"Fully matched: {stats['fully matched']}")
    print(f"Partially matched: {stats['partially matched']}")
    print(f"Not matched: {stats['not matched']}")
    print(f"Total rows in output: {len(output_records)}")

if __name__ == "__main__":
    run_match()
