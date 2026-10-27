"""Every Kafka topic name lives here; never type a topic name anywhere else."""

TICKETS_CREATED = "tickets.created"
TICKETS_ANSWERED = "tickets.answered"
TICKETS_CREATED_DLQ = "tickets.created.dlq"
TICKETS_APPROVAL_DECIDED = "tickets.approval_decided"
TICKETS_APPROVAL_DECIDED_DLQ = "tickets.approval_decided.dlq"

# name -> partitions; the create_topics command builds them (auto-create is off in Kafka).
TOPICS = {
    TICKETS_CREATED: 3,
    TICKETS_ANSWERED: 3,
    TICKETS_CREATED_DLQ: 1,
    TICKETS_APPROVAL_DECIDED: 3,
    TICKETS_APPROVAL_DECIDED_DLQ: 1,
}
