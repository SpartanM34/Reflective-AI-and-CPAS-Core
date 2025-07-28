"""Demonstration of EEP helpers for cross-agent collaboration."""

from agents.python.Telos import create_agent as create_telos, send_message as telos_send
from agents.python.Meridian import create_agent as create_meridian, send_message as meridian_send
from cpas_autogen.eep_utils import start_collab_session


def main() -> None:
    thread = "#COMM_PROTO_DEMO"
    telos = create_telos()
    meridian = create_meridian()

    # Announce a collaborative reasoning session
    start_collab_session(telos, [meridian.idp_metadata["instance_name"]], thread_token=thread, topic="EEP demo")

    # Telos provides an overview which is automatically broadcast
    response = telos_send(telos, "Provide a brief overview of the Epistemic Exchange Protocol.", thread)
    print("Telos:", response)

    # Meridian requests validation from Telos
    reply = meridian_send(
        meridian,
        "Please validate Telos's overview.",
        thread,
        validation_request="EEP overview accuracy",
    )
    print("Meridian:", reply)


if __name__ == "__main__":
    main()

