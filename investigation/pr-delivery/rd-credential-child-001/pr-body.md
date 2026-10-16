When S3 credential helpers outlive a request deadline, [`KacheCommandExecute::command_execute`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/remote_backend.rs#L1053-L1076) dropped the output future without stopping the child.

Enable termination on drop so cancellation releases helper resources.

`credential_process_releases_owned_resources` covers cancellation and ordinary completion; successful argument/profile controls and `just check` pass.
