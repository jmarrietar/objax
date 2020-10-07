export ML_DATA="data"
export PROJECT="ObjaxSSL"
export SSL_PATH=examples/classify/semi_supervised/img

./scripts/create_datasets.py


./scripts/create_unlabeled.py $ML_DATA/$PROJECT/SSL/cifar10 $ML_DATA/$PROJECT/cifar10-train.tfrecord 

export seed=3
export size=250


./scripts/create_split.py --seed=$seed --size=$size $ML_DATA/$PROJECT/SSL/cifar10 $ML_DATA/$PROJECT/cifar10-train.tfrecord



os.environ["ML_DATA"] = "data"
os.environ["PROJECT"] = "ObjaxSSL"

-------------------------------------------------

export seed=3
export size=4000

./scripts/create_datasets.py

./scripts/create_unlabeled.py $ML_DATA/$PROJECT/SSL/voets $ML_DATA/$PROJECT/voets-train.tfrecord 

./scripts/create_split.py --seed=$seed --size=$size $ML_DATA/$PROJECT/SSL/voets $ML_DATA/$PROJECT/voets-train.tfrecord

-------------------------------------------------
export ML_DATA="data"
export PROJECT="ObjaxSSL"
export seed=3
export size=10

./scripts/create_datasets.py

./scripts/create_unlabeled.py $ML_DATA/$PROJECT/SSL/voets $ML_DATA/$PROJECT/voets-train.tfrecord 

./scripts/create_split.py --seed=$seed --size=$size $ML_DATA/$PROJECT/SSL/voets $ML_DATA/$PROJECT/voets-train.tfrecord

python fixmatch.py --dataset=voets.3@10-0 --unlabeled=voets --uratio=5 --augment='CTA(sm,sm,sm)'