"""Account management tools for Universal Email MCP Server."""

from .. import config, models


async def add_account(data: models.AddAccountInput) -> models.StatusOutput:
    """Add a new email account configuration."""
    try:
        settings = config.get_settings(reload=True)

        if settings.get_account(data.account_name):
            return models.StatusOutput(
                status="error",
                details=f"Account '{data.account_name}' already exists. Use a different name or remove the existing account first."
            )

        new_account = config.EmailSettings(
            account_name=data.account_name,
            full_name=data.full_name,
            email_address=data.email_address,
            incoming=config.EmailServer(
                user_name=data.user_name,
                password=data.password,
                host=data.imap_host,
                port=data.imap_port,
                use_ssl=data.imap_use_ssl,
                verify_ssl=data.imap_verify_ssl
            ),
            outgoing=config.EmailServer(
                user_name=data.user_name,
                password=data.password,
                host=data.smtp_host,
                port=data.smtp_port,
                use_ssl=data.smtp_use_ssl,
                verify_ssl=data.smtp_verify_ssl
            )
        )

        settings.add_account(new_account)
        settings.store()

        return models.StatusOutput(
            status="success",
            details=f"Account '{data.account_name}' added successfully."
        )

    except Exception as e:
        return models.StatusOutput(
            status="error",
            details=f"Failed to add account: {str(e)}"
        )


async def list_accounts() -> models.ListAccountsOutput:
    """List all configured email accounts."""
    try:
        settings = config.get_settings(reload=True)
        account_names = [acc.account_name for acc in settings.accounts]
        return models.ListAccountsOutput(accounts=account_names)
    except Exception:
        return models.ListAccountsOutput(accounts=[])


async def remove_account(data: models.RemoveAccountInput) -> models.StatusOutput:
    """Remove an email account configuration."""
    try:
        settings = config.get_settings(reload=True)

        if not settings.get_account(data.account_name):
            return models.StatusOutput(
                status="error",
                details=f"Account '{data.account_name}' not found."
            )

        removed = settings.remove_account(data.account_name)
        if removed:
            settings.store()
            return models.StatusOutput(
                status="success",
                details=f"Account '{data.account_name}' removed successfully."
            )
        else:
            return models.StatusOutput(
                status="error",
                details=f"Failed to remove account '{data.account_name}'."
            )

    except Exception as e:
        return models.StatusOutput(
            status="error",
            details=f"Failed to remove account: {str(e)}"
        )


def get_account_settings(account_name: str) -> config.EmailSettings:
    """Get account settings by name, raising ValueError if not found."""
    settings = config.get_settings()
    account = settings.get_account(account_name)
    if not account:
        raise ValueError(f"Account '{account_name}' not found")
    return account
