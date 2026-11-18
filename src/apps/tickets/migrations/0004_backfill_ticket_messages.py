"""Older tickets get their question and answer as messages, so every ticket shows the same conversation view."""

from django.db import migrations


def backfill(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    TicketMessage = apps.get_model("tickets", "TicketMessage")
    rows = []
    for ticket in Ticket.objects.filter(messages__isnull=True).iterator():
        rows.append(TicketMessage(tenant_id=ticket.tenant_id, ticket=ticket, author="customer", body=ticket.body, answered_at=ticket.answered_at))
        if ticket.reply:
            rows.append(TicketMessage(tenant_id=ticket.tenant_id, ticket=ticket, author="assistant", body=ticket.reply))
    TicketMessage.objects.bulk_create(rows, batch_size=500)
    # auto_now_add stamps them all "now"; copy the ticket's times so the order and dates stay true.
    for message in TicketMessage.objects.select_related("ticket").iterator():
        stamp = message.ticket.answered_at if message.author == "assistant" and message.ticket.answered_at else message.ticket.created_at
        TicketMessage.objects.filter(pk=message.pk).update(created_at=stamp)


class Migration(migrations.Migration):
    dependencies = [("tickets", "0003_ticket_messages")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
