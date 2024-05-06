# 2scht

<p align="center">
    <img src="assets/images/logo.jpg"/>
</p>

To run the service run the following command, which will spin up a single server for all three vendors - **vk**, **sber** and **yandex**:

```sh
python -m skill serve
```

To expose the service through `https` use [ngrok](https://ngrok.com/docs/http/).

# How to use

1. Say something like `Запусти навык 'Оранжевая нить'` to list available threads. Only a few options with the largest number of comments will be listed due to api constraints on the maximum number of characters - this group of thread headers will be further referred as a `page`. To move to the next page, say the phrase again;
1. Say something like `Возьми второй` to start voicing out the Nth thread from the provided list. Only some number of first comments will be voiced out because of the api constraints on the maximum number of characters - this batch of comments is further referred as a `segment`;
1. Say `Стоп` to stop voicing out the thread;
1. Say something like `Запусти скилл Оранжевая нить` if you've finished listening to a thread `segment` (a consequtive list of comments) and want to move to the next `segment` of the same thread;
1. Say something like `Давай поиграем в нити` to repeat the last thread `segment`;
1. Say something like `Давай вперед` while the agent is voicing out a thread `segment` to stop listening to the current thread and move to the next thread;
1. Say something like `Давай назад` while the agent is voicing out a thread `segment` to stop listening to the current thread and move to the previous one.
