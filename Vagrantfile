Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/bionic64"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
    vb.cpus = "2"
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt install -y python3-pip
    pip3 install nltk
    pip3 install -U pip
    pip3 install -U setuptools
    pip3 install -U wheel
    pip3 install -U spacy==2.2.4
    python3 -m spacy download en_core_web_sm
    cp -r /vagrant/src/ /home/vagrant/
    cp -r /vagrant/dataset/ /home/vagrant/
  SHELL
end
