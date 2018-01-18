# Change log

## Version 0.x.x

### Version 0.1.20

- Fix comparision between in and CombinedExpression [more information](https://stackoverflow.com/questions/33672920/django-db-models-f-combined-expression)

### Version 0.1.19

- Make migration files

### Version 0.1.18

- Create index for: `(routing_key, updated_at)`, `status`
- Add status `STATUS__MAX_ATTEMPT = 3`
- Create `QueueProcessFacade.MAX_ATTEMPT` attribute, if `event.attempt` >= `QueueProcessFacade.MAX_ATTEMPT` then set status of event to `STATUS__MAX_ATTEMPT`

### Version 0.1.17

- Set channel is None when close
- Create `handle` method for child(ren) override.

### Version 0.1.16

- Raise exception if there is no cache service

### Version 0.1.15

- Release lock task when has exception

### Version 0.1.14

- Fix bug update close event

### Version 0.1.13

- Fix bug release lock task

### Version 0.1.12

- Using single channel
- Limit record when getting list
- Update close_event method, return 