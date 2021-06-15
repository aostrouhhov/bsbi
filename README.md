# BSBI
Task for Information Retrieaval course - Blocked Sort-Basing Indexing

Dataset was taken from here: http://kopiwiki.dsd.sztaki.hu/

## Getting started
Project structure:
```
dataset/             - testing dataset
src/bsbi.py          - Blocked Sort-Basing Indexing algorithm implementation
src/build_index.py   - BSBI runner
src/find.py          - Search runner
src/operators.py     - Boolean operators used in search query
src/shunting_yard.py - Shunting Yard algorithm implementation for search query parsing
```

### Development

Run and provision the VM with Vagrant
```
$ vagrant up
```

Connect to the VM
```
$ vagrant ssh
```

`src` and `dataset` folders should have been copied to `/home/vagrant`. You can edit source code _on your machine_ with your favourite editor.

Just sync when you want to see your edits in the VM:
```
$ rsync -a /vagrant/src/ /home/vagrant/src/
```

### Run
Run and provision the VM with Vagrant
```
$ vagrant up
```

Connect to the VM
```
$ vagrant ssh
```

Build index:
```
$ python3 src/build_index.py
```
```
Flags:
  -s SIZE, --size SIZE  Block size in KB (def: "10240" aka 10 MB)
  -d DIR, --dir DIR     Path to directory with text corpus (def: "dataset")
```

Run search:
```
$ python3 src/find.py
```

Enter your query, for example: `woodbridge AND NOT sturbridge`

## Main concept (Russian)
Строим индекс методом BSBI.
```
список_пар = []
упорядоченный_словарь = []
блок_ид = 0
документ_ид = 0

ДЛЯ КАЖДОГО документа:
    Сделать токенизацию;
    Сделать лемматизацию;
    # получаем список термов для документа: [doc1] -> [term1, term2])
    Добавить в список_пар (term1, doc1), (term2, doc1), (term3, doc1) и т.д.

    ЕСЛИ размер списка_пар >= размер блока ИЛИ больше нет документов:
        Сортировать списк_пар
        Сделать из списка_пар упорядоченный словарь с постингами вида [term] -> [doc1, doc2, doc3]
        Пройтись по словарю и записать постинги на диск

        ЕСЛИ документы еще есть:
            # переходим к следующему блоку
            список_пар = []
            упорядоченный_словарь = []
            блок_ид+=1

        ИНАЧЕ:
            Прерываем и делаем слияние блоков на диске

    документ_ид+=1
```